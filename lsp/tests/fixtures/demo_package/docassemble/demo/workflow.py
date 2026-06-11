def case_title(name):
    return f"Case for {name}"


def workflow_summary(stage):
    return f"Workflow stage: {stage}"


class WorkflowState:
    @staticmethod
    def status_label(stage):
        return f"Stage: {stage}"
