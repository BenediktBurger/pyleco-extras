
from inspect import getmembers
from typing import Optional, TypeVar, Generic

from pymeasure.instruments import Channel

from pyleco.core.internal_protocols import CommunicatorProtocol
from pyleco.directors.director import Director
from pyleco.directors.transparent_director import RemoteCall


Device = TypeVar("Device")


def property_creator(name: str,
                     original_property: property,
                     ) -> property:
    """Create a property which gets/sets the remote properties value."""
    if original_property.fget is None:
        fget = None
    else:
        def getter(self):
            return self.director.get_parameters((name,)).get(name)
        fget = getter
    if original_property.fset is None:
        fset = None
    else:
        def setter(self, value):
            return self.director.set_parameters({name: value})
        fset = setter
    return property(fget, fset, doc=original_property.__doc__)


def create_device_copy(device_class: type[Device], director: Director, path: str = "",
                       ) -> Device:
    """Create an instance with the same methods and attributes as the given class.
    This instance, however, calls methods of the `director` instead.

    :param path: Path internal in the instrument, for example with channels.
    """
    if path:
        path = path + "."

    class DeviceCopy:
        def __init__(self, director: Director):
            self.director = director

        def call_action(self, action: str, *args, **kwargs):
            self.director.call_action(action, *args, **kwargs)

    for name, member in getmembers(device_class):
        if name.startswith("_"):
            continue  # do not make private methods/variables accessible
        if isinstance(member, property):
            setattr(DeviceCopy, name, property_creator(path + name, member))
        elif callable(member):
            setattr(DeviceCopy, name, RemoteCall(name=path + name, doc=member.__doc__))
        # Channels of pymeasure
        elif isinstance(member, Channel.ChannelCreator):
            channel_class = member.pairs[0][0]
            setattr(DeviceCopy, name, create_device_copy(device_class=channel_class,
                                                         director=director,
                                                         path=path + name))
        elif isinstance(member, Channel.MultiChannelCreator):
            prefix = member.kwargs.get("prefix")
            for cls, id in member.pairs:
                c_name = f"{prefix}{id}"
                setattr(DeviceCopy, c_name, create_device_copy(cls, director=director,
                                                               path=path + c_name))
        else:
            # TODO plain attributes (int, str, float, list...) are not found: Combine with
            # TransparentDirector?
            continue

    return DeviceCopy(director)  # type: ignore


class AnalyzingDirector(Director, Generic[Device]):
    """This Director analyzes an instrument class and behaves like that instrument, but directs
    an Actor, which controls such an instrument.
    """
    device: Device

    def __init__(self,
                 device_class: type[Device],
                 actor: Optional[bytes | str] = None,
                 communicator: Optional[CommunicatorProtocol] = None,
                 name: str = "Director",
                 **kwargs):
        super().__init__(actor=actor, communicator=communicator, name=name, **kwargs)
        self.device = create_device_copy(device_class=device_class,
                                         director=self)
