import logging

import import_declare_test  # noqa
from github_actions_workflow_runs_for_splunk_rh import DeleteCheckpointExternalHandler
from splunktaucclib.rest_handler import admin_external, util
from splunktaucclib.rest_handler.admin_external import AdminExternalHandler
from splunktaucclib.rest_handler.endpoint import (
    DataInputModel,
    RestModel,
    field,
    validator,
)

util.remove_http_proxy_env_vars()


fields = [
    field.RestField(
        "interval",
        required=True,
        encrypted=False,
        default="300",
        validator=validator.Pattern(
            regex=r"""^\-[1-9]\d*$|^\d*$""",
        ),
    ),
    field.RestField(
        "index",
        required=True,
        encrypted=False,
        default="default",
        validator=validator.String(
            max_len=80,
            min_len=1,
        ),
    ),
    field.RestField(
        "github_username", required=True, encrypted=False, default=None, validator=None
    ),
    field.RestField(
        "github_repo", required=True, encrypted=False, default=None, validator=None
    ),
    field.RestField(
        "github_pat", required=True, encrypted=False, default=None, validator=None
    ),
    field.RestField("disabled", required=False, validator=None),
]
model = RestModel(fields, name=None)


endpoint = DataInputModel(
    "github_actions_workflow_stats",
    model,
)


if __name__ == "__main__":
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=DeleteCheckpointExternalHandler,
    )
