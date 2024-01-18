
from unittest.mock import MagicMock

import pytest

from pymeasure.instruments import Instrument, Channel
from pyleco.core.message import Message, MessageTypes
from pyleco.test import FakeCommunicator

from devices.pyleco_addons.analyzing_director import (create_device_copy, AnalyzingDirector,
                                                      RemoteCall)


cid = b"conversation_id;"


def empty_getter(self):
    pass


def empty_setter(self, value):
    pass


class ExampleChannel(Channel):
    channel_property = property(fget=empty_getter, fset=empty_setter, doc="Channel Property")

    def channel_method(self):
        """Channel Method"""
        pass


class ExampleInstrument:

    channel = Instrument.ChannelCreator(cls=ExampleChannel, id=1)

    mchannels = Instrument.MultiChannelCreator(cls=ExampleChannel, id=(2, 3))

    get_property = property(fget=empty_getter, doc="Getter")

    set_property = property(fset=empty_setter, doc="Setter")

    control_property = property(fget=empty_getter, fset=empty_setter, doc="Controller")

    def method(self, *args, **kwargs):
        """Method"""
        pass


def get_parameters_fake(parameters):
    pars = {}
    for i, par in enumerate(parameters):
        pars[par] = i
    return pars


class FakeDirector:
    device: ExampleInstrument

    def __init__(self):
        self.call_action = MagicMock()
        self.get_parameters = MagicMock()
        self.get_parameters.side_effect = get_parameters_fake
        self.set_parameters = MagicMock()


@pytest.fixture
def instrument_cls():
    cls = create_device_copy(ExampleInstrument,
                             director=None)  # type: ignore
    return cls.__class__


@pytest.fixture(scope="function")
def fake_director():
    director = FakeDirector()
    director.device = create_device_copy(device_class=ExampleInstrument,
                                         director=director)  # type: ignore
    return director


class TestGetter:
    @pytest.fixture
    def getter(self, instrument_cls):
        return instrument_cls.get_property

    def test_property(self, getter):
        assert isinstance(getter, property)

    def test_getter(self, getter):
        assert getter.fget is not None

    def test_no_setter(self, getter):
        assert getter.fset is None

    def test_get_parameters(self, fake_director: FakeDirector):
        assert fake_director.device.get_property == 0
        fake_director.get_parameters.assert_called_once_with(("get_property",))


class TestSetter:
    @pytest.fixture
    def setter(self, instrument_cls):
        return instrument_cls.set_property

    def test_property(self, setter):
        assert isinstance(setter, property)

    def test_no_getter(self, setter):
        assert setter.fget is None

    def test_setter(self, setter):
        assert setter.fset is not None

    def test_set_parameters(self, fake_director: FakeDirector):
        fake_director.device.set_property = 5
        fake_director.set_parameters.assert_called_once_with({'set_property': 5})


class TestController:
    @pytest.fixture
    def controller(self, instrument_cls):
        return instrument_cls.control_property

    def test_property(self, controller):
        assert isinstance(controller, property)

    def test_getter(self, controller):
        assert controller.fget is not None

    def test_setter(self, controller):
        assert controller.fset is not None


class TestMethod:
    def test_method(self, instrument_cls):
        method = instrument_cls.method
        assert isinstance(method, RemoteCall)

    def test_doc(self, fake_director: FakeDirector):
        assert fake_director.device.method.__doc__ == "Method"

    def test_call_action(self, fake_director: FakeDirector):
        fake_director.device.method(5, kwarg=7)
        fake_director.call_action.assert_called_once_with("method", 5, kwarg=7)


class TestChannelProperty:
    @pytest.fixture
    def prop(self, instrument_cls):
        return instrument_cls.channel.channel_property

    def test_get_property(self, fake_director: FakeDirector):
        assert fake_director.device.channel.channel_property == 0  # type: ignore
        fake_director.get_parameters.assert_called_once_with(("channel.channel_property",))

    def test_get_property_of_multiCreator(self, fake_director: FakeDirector):
        assert fake_director.device.ch_2.channel_property == 0  # type: ignore
        fake_director.get_parameters.assert_called_once_with(("ch_2.channel_property",))

    def test_set_property(self, fake_director: FakeDirector):
        fake_director.device.channel.channel_property = 7  # type: ignore
        fake_director.set_parameters.assert_called_once_with({'channel.channel_property': 7})

    def test_set_property_of_multiCreator(self, fake_director: FakeDirector):
        fake_director.device.ch_2.channel_property = 9  # type: ignore
        fake_director.set_parameters.assert_called_once_with({'ch_2.channel_property': 9})

    def test_method(self, fake_director: FakeDirector):
        fake_director.device.channel.channel_method(5, kwarg=7)  # type: ignore
        fake_director.call_action.assert_called_once_with("channel.channel_method", 5, kwarg=7)


class TestAnalyzingDirectorInit:
    @pytest.fixture
    def director(self, monkeypatch):
        def fake_generate_conversation_id():
            return cid
        monkeypatch.setattr("pyleco.core.serialization.generate_conversation_id",
                            fake_generate_conversation_id)
        return AnalyzingDirector(device_class=ExampleInstrument,
                                 actor="Actor",
                                 communicator=FakeCommunicator("Director"))

    def test_device_with_property(self, director: AnalyzingDirector):
        director.communicator._r = [  # type: ignore
            Message("Director", "Actor", message_type=MessageTypes.JSON, conversation_id=cid, data={
                "jsonrpc": "2.0", "id": 1, "result": {'get_property': 5}
            })]
        result = director.device.get_property  # type: ignore
        assert director.communicator._s == [  # type: ignore
            Message("Actor", "Director", message_type=MessageTypes.JSON, conversation_id=cid, data={
                "jsonrpc": "2.0", "method": "get_parameters",
                "params": {'parameters': ('get_property',)}, "id": 1,
            })
        ]
        assert result == 5
