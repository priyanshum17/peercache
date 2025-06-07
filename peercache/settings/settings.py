import json
from pydantic import BaseModel, Field


class Settings(BaseModel):
    NETWORK_DATA_PATH: str = Field(default=None)
    NETWORKS_FOLDER_PATH: str = Field(default=None)
    PEER_FOLDER_PATH: str = Field(default=None)

    @classmethod
    def from_json(cls, json_path: str) -> "Settings":
        with open(json_path, "r") as f:
            data = json.load(f)
        return cls(**data)


SETTINGS = Settings.from_json("config.json")
