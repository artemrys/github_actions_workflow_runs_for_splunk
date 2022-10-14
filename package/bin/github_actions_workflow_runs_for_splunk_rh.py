import traceback

import import_declare_test  # noqa: 401
from github_actions_workflow_constants import APP_NAME
from solnlib import log
from solnlib.modular_input import checkpointer
from splunktaucclib.rest_handler import admin_external


class DeleteCheckpointExternalHandler(admin_external.AdminExternalHandler):
    def __init__(self, *args, **kwargs):
        admin_external.AdminExternalHandler.__init__(self, *args, **kwargs)

    def handleList(self, conf_info):
        admin_external.AdminExternalHandler.handleList(self, conf_info)

    def handleEdit(self, conf_info):
        admin_external.AdminExternalHandler.handleEdit(self, conf_info)

    def handleCreate(self, conf_info):
        admin_external.AdminExternalHandler.handleCreate(self, conf_info)

    def handleRemove(self, conf_info):
        self.delete_checkpoint()
        admin_external.AdminExternalHandler.handleRemove(self, conf_info)

    def delete_checkpoint(self):
        log_filename = "github_actions_workflow_runs_delete_checkpoint"
        logger = log.Logs().get_logger(log_filename)
        input_name = str(self.callerArgs.id)
        session_key = self.getSessionKey()
        try:
            normalized_input_name = input_name.split("/")[-1]
            collection_name = (
                f"github_actions_workflow_runs_for_splunk_{normalized_input_name}"
            )
            checkpointer_service = checkpointer.KVStoreCheckpointer(
                collection_name,
                session_key,
                APP_NAME,
            )
            checkpointer_service.delete("checkpoint")
            logger.info(f"Removed KVStore checkpoint for {collection_name}")
        except Exception:
            logger.error(
                f"Error while deleting checkpoint for {input_name} input. {traceback.format_exc()}"
            )
