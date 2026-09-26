class NotificationProvider:
    channel: str

    def send(self, *, recipient: str, template: str, context: dict) -> str:
        raise NotImplementedError
