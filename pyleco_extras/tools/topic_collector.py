
import time

from pyleco.utils.listener import Listener
from pyleco.core.data_message import DataMessage


class TopicCollector(Listener):

    def __init__(self, name="asfdjsadlkf jksladfj", **kwargs):
        super().__init__(name=name, **kwargs)
        self.topics = []

    def start_listen(self) -> None:
        super().start_listen()
        self.message_handler.handle_subscription_data = self.handle_subscription_data  # type:ignore
        self.message_handler.handle_subscription_message = self.handle_subscription_message  # type: ignore  # noqa

    def handle_subscription_data(self, data: dict):
        for key in data:
            self.add_topic(key)

    def handle_subscription_message(self, message: DataMessage):
        self.add_topic(message.topic.decode())

    def add_topic(self, topic: str):
        if topic not in self.topics:
            self.topics.append(topic)


def print_topics(collection_time: float = 10):
    """Collect and print topics.

    :param collection_time: Time to collect in seconds.
    """
    print(f"Start to collect published topics for {collection_time} seconds.")
    listener = TopicCollector()
    listener.start_listen()
    listener.communicator.subscribe("")
    time.sleep(collection_time)
    listener.stop_listen()
    print("Topcis are: ", listener.topics)


if __name__ == "__main__":
    print_topics()
