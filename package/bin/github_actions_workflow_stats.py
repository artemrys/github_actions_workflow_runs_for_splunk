import datetime
import json
import logging
import sys
import time
import traceback

import import_declare_test  # noqa
import requests
from github_actions_workflow_constants import APP_NAME
from solnlib import conf_manager, log, modular_input
from splunklib import modularinput as smi


def _get_github_pat(session_key: str, account_name: str) -> str:
    cfm = conf_manager.ConfManager(
        session_key,
        APP_NAME,
        realm=f"__REST_CREDENTIAL__#{APP_NAME}#configs/conf-github_actions_workflow_runs_for_splunk_github_pats",
    )
    github_pats_conf = cfm.get_conf(
        "github_actions_workflow_runs_for_splunk_github_pats"
    )
    return github_pats_conf.get(account_name).get("pat")


def _str_to_seconds(timestamp: str) -> float:
    timestamp_without_z = timestamp.replace("Z", "")
    d = datetime.datetime.fromisoformat(timestamp_without_z)
    return time.mktime(d.timetuple())


def _logger_for_input(input_name: str) -> logging.Logger:
    return log.Logs().get_logger(
        f"github_actions_workflow_runs_for_splunk_{input_name}"
    )


def _get_workflow_runs_for_repo(
    logger: logging.Logger,
    username: str,
    repo: str,
    token: str,
    created: str,
):
    results = []
    page = 1
    while True:
        start_time = time.time()
        url = f"https://api.github.com/repos/{username}/{repo}/actions/runs"
        response = requests.get(
            url,
            params={
                "created": created,
                "page": page,
                "per_page": 100,
            },
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"token {token}",
            },
            timeout=60,
        )
        end_time = time.time()
        request_time = round(end_time - start_time, 4)
        logger.debug(f"Request to {url} took {request_time}")
        response.raise_for_status()
        workflow_runs = response.json()["workflow_runs"]
        if len(workflow_runs) == 0:
            break
        results.extend(workflow_runs)
        page += 1
    return results


class Input(smi.Script):
    def __init__(self):
        super().__init__()

    def get_scheme(self):
        scheme = smi.Scheme("github_actions_workflow_stats")
        scheme.description = "github_actions_workflow_stats input"
        scheme.use_external_validation = True
        scheme.streaming_mode_xml = True
        scheme.use_single_instance = False
        scheme.add_argument(
            smi.Argument(
                "name", title="Name", description="Name", required_on_create=True
            )
        )
        scheme.add_argument(
            smi.Argument(
                "github_username",
                title="GitHub username",
                description="GitHub username",
                required_on_create=True,
            )
        )
        scheme.add_argument(
            smi.Argument(
                "github_repo",
                title="GitHub repo",
                description="GitHub repo",
                required_on_create=True,
            )
        )
        return scheme

    def validate_input(self, definition):
        return

    def stream_events(self, inputs: smi.InputDefinition, event_writer: smi.EventWriter):
        for input_name, input_item in inputs.inputs.items():
            normalized_input_name = input_name.split("/")[-1]
            logger = _logger_for_input(normalized_input_name)
            try:
                session_key = self._input_definition.metadata["session_key"]
                log_level = conf_manager.get_log_level(
                    logger=logger,
                    session_key=session_key,
                    app_name=APP_NAME,
                    conf_name="github_actions_workflow_runs_for_splunk_settings",
                )
                logger.setLevel(log_level)
                checkpoint_collection = (
                    f"github_actions_workflow_runs_for_splunk_{normalized_input_name}"
                )
                github_username = input_item.get("github_username")
                github_repo = input_item.get("github_repo")
                checkpointer = modular_input.KVStoreCheckpointer(
                    checkpoint_collection,
                    session_key,
                    APP_NAME,
                )
                checkpoint = checkpointer.get("checkpoint")
                if checkpoint is not None:
                    checkpoint = checkpoint.get("checkpoint")
                    logger.info(f"Stored checkpoint {checkpoint}")
                else:
                    now = datetime.datetime.utcnow()
                    now_minus_30_days = now - datetime.timedelta(days=1)
                    checkpoint = now_minus_30_days.isoformat("T", "milliseconds")
                    logger.info(f"Created checkpoint {checkpoint}")
                created = ":>" + checkpoint
                github_token = _get_github_pat(
                    session_key, input_item.get("github_pat")
                )
                logger.info(
                    f"Getting workflow runs for {github_username}/{github_repo}"
                )
                workflow_runs = _get_workflow_runs_for_repo(
                    logger,
                    github_username,
                    github_repo,
                    github_token,
                    created,
                )
                if len(workflow_runs) > 0:
                    logger.info(f"Got {len(workflow_runs)} workflow runs")
                    for workflow_run in workflow_runs:
                        event_time = workflow_run["run_started_at"]
                        event_time_seconds = _str_to_seconds(event_time)
                        event = smi.Event(
                            data=json.dumps(workflow_run),
                            time=event_time_seconds,
                            index=input_item["index"],
                            sourcetype="github:workflow_runs",
                        )
                        event_writer.write_event(event)
                        logger.info(f"Event written that occured @ {event_time}")
                    latest_event_time = workflow_runs[0]["run_started_at"]
                    checkpointer.update(
                        "checkpoint",
                        {"checkpoint": latest_event_time},
                    )
                    logger.info(f"Saved checkpoint @ {latest_event_time}")
                else:
                    logger.info("Got 0 workflow runs")
                    checkpoint_time = datetime.datetime.utcnow().isoformat(
                        "T", "milliseconds"
                    )
                    checkpointer.update(
                        "checkpoint",
                        {"checkpoint": checkpoint_time},
                    )
                    logger.info(f"Saved checkpoint @ {checkpoint_time}")
            except Exception as e:
                logger.error(
                    f"Exception raised while ingesting GitHub Action workflow "
                    f"runs: {e}. Traceback: {traceback.format_exc()}"
                )


if __name__ == "__main__":
    exit_code = Input().run(sys.argv)
    sys.exit(exit_code)
