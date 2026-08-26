from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from yarl import URL

from plexio.models.plex import PlexLibrarySection, Resolution
from plexio.models.utils import to_camel


class ServerConfiguration(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        arbitrary_types_allowed=True,
    )

    access_token: str
    discovery_url: URL
    streaming_url: URL
    server_name: str
    sections: list[PlexLibrarySection] = Field(default_factory=list)

    _extract_discovery_url = field_validator('discovery_url', mode='before')(URL)
    _extract_streaming_url = field_validator('streaming_url', mode='before')(URL)


class AddonConfiguration(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        arbitrary_types_allowed=True,
    )

    servers: list[ServerConfiguration] = Field(min_length=1)
    version: str = '0.0.1'
    include_transcode_original: bool = False
    include_transcode_down: bool = False
    transcode_down_qualities: list[Resolution] = Field(default_factory=list)
    include_plex_tv: bool = False
    include_catalogs: bool = True

    @model_validator(mode='before')
    @classmethod
    def _legacy_flat_to_servers(cls, data):
        if not isinstance(data, dict):
            return data
        if 'servers' not in data and 'accessToken' in data:
            data['servers'] = [
                {
                    'accessToken': data['accessToken'],
                    'discoveryUrl': data['discoveryUrl'],
                    'streamingUrl': data['streamingUrl'],
                    'serverName': data.get('serverName', ''),
                    'sections': data.get('sections', []),
                }
            ]
        return data
