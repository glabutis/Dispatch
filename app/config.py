import json
import os
import uuid
from dataclasses import asdict, dataclass, field
from typing import List, Optional

CONFIG_DIR = os.path.expanduser("~/.config/dispatch")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")


@dataclass
class Template:
    id: str
    label: str
    address: str
    args: str = ""

    @classmethod
    def new(cls) -> "Template":
        return cls(id=str(uuid.uuid4()), label="", address="", args="")

    def copy(self) -> "Template":
        return Template(**asdict(self))


@dataclass
class Mapping:
    id: str
    name: str
    key_str: str           # serialized pynput key, e.g. "Key.right" or "a"
    press_type: str        # "short" | "long" | "any"
    osc_address: str       # e.g. "/atem/cut"
    osc_args: str          # space-separated args string, e.g. "1" or "1 2.5"
    enabled: bool = True
    template_id: Optional[str] = None   # None = manual/custom command
    toggle_mode: bool = False
    osc_address_b: str = ""
    osc_args_b: str = ""
    destination_ids: List[str] = field(default_factory=list)  # empty = all enabled

    @classmethod
    def new(cls, name: str = "New Mapping") -> "Mapping":
        return cls(
            id=str(uuid.uuid4()),
            name=name,
            key_str="",
            press_type="short",
            osc_address="",
            osc_args="",
            enabled=True,
            template_id=None,
            toggle_mode=False,
            osc_address_b="",
            osc_args_b="",
            destination_ids=[],
        )

    def copy(self) -> "Mapping":
        d = asdict(self)
        return Mapping(**d)


@dataclass
class OSCDestination:
    id: str
    name: str
    host: str
    port: int
    enabled: bool = True

    @classmethod
    def new(cls, name: str = "Default", host: str = "127.0.0.1", port: int = 3333) -> "OSCDestination":
        return cls(id=str(uuid.uuid4()), name=name, host=host, port=port)

    def copy(self) -> "OSCDestination":
        return OSCDestination(**asdict(self))


@dataclass
class Profile:
    id: str
    name: str
    mappings: List[Mapping] = field(default_factory=list)

    @classmethod
    def new(cls, name: str = "Default") -> "Profile":
        return cls(id=str(uuid.uuid4()), name=name)

    def copy(self) -> "Profile":
        return Profile(
            id=self.id,
            name=self.name,
            mappings=[m.copy() for m in self.mappings],
        )


@dataclass
class AppSettings:
    long_press_threshold_ms: int = 500
    theme: str = "dark"   # "dark" | "light"


@dataclass
class AppConfig:
    destinations: List[OSCDestination] = field(default_factory=lambda: [OSCDestination.new()])
    settings: AppSettings = field(default_factory=AppSettings)
    profiles: List[Profile] = field(default_factory=lambda: [Profile.new()])
    templates: List[Template] = field(default_factory=list)
    active_profile_id: str = ""
    toggle_states: dict = field(default_factory=dict)  # mapping_id -> bool, persisted

    def __post_init__(self) -> None:
        if not self.active_profile_id and self.profiles:
            self.active_profile_id = self.profiles[0].id

    @property
    def active_profile(self) -> Profile:
        return next(
            (p for p in self.profiles if p.id == self.active_profile_id),
            self.profiles[0],
        )

    def save(self) -> None:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        data = {
            "destinations": [asdict(d) for d in self.destinations],
            "settings": asdict(self.settings),
            "profiles": [
                {
                    "id": p.id,
                    "name": p.name,
                    "mappings": [asdict(m) for m in p.mappings],
                }
                for p in self.profiles
            ],
            "templates": [asdict(t) for t in self.templates],
            "active_profile_id": self.active_profile_id,
            "toggle_states": self.toggle_states,
        }
        with open(CONFIG_FILE, "w") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def load_default(cls) -> "AppConfig":
        if not os.path.exists(CONFIG_FILE):
            return cls()
        try:
            with open(CONFIG_FILE) as f:
                data = json.load(f)

            raw_settings = data.get("settings", {})
            settings = AppSettings(
                **{k: v for k, v in raw_settings.items() if k in AppSettings.__dataclass_fields__}
            )

            templates = [Template(**t) for t in data.get("templates", [])]

            # Destinations — migrate old "osc" key
            if "destinations" in data:
                destinations = [OSCDestination(**d) for d in data["destinations"]]
            elif "osc" in data:
                osc = data["osc"]
                destinations = [
                    OSCDestination(
                        id=str(uuid.uuid4()),
                        name="Default",
                        host=osc.get("host", "127.0.0.1"),
                        port=osc.get("port", 3333),
                    )
                ]
            else:
                destinations = [OSCDestination.new()]

            # Profiles — migrate old "mappings" key
            if "profiles" in data:
                profiles = []
                for p in data["profiles"]:
                    mappings = _parse_mappings(p.get("mappings", []))
                    profiles.append(Profile(id=p["id"], name=p["name"], mappings=mappings))
            elif "mappings" in data:
                mappings = _parse_mappings(data["mappings"])
                profiles = [Profile(id=str(uuid.uuid4()), name="Default", mappings=mappings)]
            else:
                profiles = [Profile.new()]

            active_profile_id = data.get("active_profile_id", "")
            if not active_profile_id or not any(p.id == active_profile_id for p in profiles):
                active_profile_id = profiles[0].id

            # Load toggle states; prune IDs that no longer belong to a toggle-mode mapping
            toggle_mapping_ids = {
                m.id for p in profiles for m in p.mappings if m.toggle_mode
            }
            raw_ts = data.get("toggle_states", {})
            toggle_states = {
                k: bool(v) for k, v in raw_ts.items()
                if isinstance(k, str) and k in toggle_mapping_ids
            }

            return cls(
                destinations=destinations,
                settings=settings,
                profiles=profiles,
                templates=templates,
                active_profile_id=active_profile_id,
                toggle_states=toggle_states,
            )
        except Exception:
            return cls()


def _parse_mappings(raw_list: list) -> List[Mapping]:
    result = []
    fields = Mapping.__dataclass_fields__
    for m in raw_list:
        m.setdefault("toggle_mode", False)
        m.setdefault("osc_address_b", "")
        m.setdefault("osc_args_b", "")
        m.setdefault("destination_ids", [])
        m.setdefault("template_id", None)
        result.append(Mapping(**{k: v for k, v in m.items() if k in fields}))
    return result
