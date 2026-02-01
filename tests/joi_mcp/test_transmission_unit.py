from enum import Enum
from unittest.mock import MagicMock

import pytest

from joi_mcp.transmission import Torrent, TorrentList, _torrent_to_model


class FakeStatus(Enum):
    DOWNLOADING = "downloading"
    SEEDING = "seeding"
    STOPPED = "stopped"


def make_fake_torrent(
    id=1,
    name="Test Torrent",
    status=FakeStatus.DOWNLOADING,
    progress=50.0,
    rate_download=1024,
    rate_upload=512,
    eta=3600,
):
    t = MagicMock()
    t.id = id
    t.name = name
    t.status = status
    t.progress = progress
    t.rate_download = rate_download
    t.rate_upload = rate_upload
    t.eta = eta
    return t


@pytest.mark.unit
class TestModels:
    def test_torrent_parses_full_response(self):
        data = {
            "id": 1,
            "name": "Ubuntu 24.04",
            "status": "downloading",
            "progress": 45.5,
            "download_speed": 1024000,
            "upload_speed": 512000,
            "eta": 3600,
        }
        torrent = Torrent.model_validate(data)
        assert torrent.id == 1
        assert torrent.name == "Ubuntu 24.04"
        assert torrent.status == "downloading"
        assert torrent.progress == 45.5
        assert torrent.download_speed == 1024000
        assert torrent.upload_speed == 512000
        assert torrent.eta == 3600

    def test_torrent_handles_none_eta(self):
        data = {
            "id": 2,
            "name": "Completed Torrent",
            "status": "seeding",
            "progress": 100.0,
            "download_speed": 0,
            "upload_speed": 256000,
            "eta": None,
        }
        torrent = Torrent.model_validate(data)
        assert torrent.eta is None

    def test_torrent_list_model(self):
        data = {
            "torrents": [
                {
                    "id": 1,
                    "name": "Torrent 1",
                    "status": "downloading",
                    "progress": 50.0,
                    "download_speed": 1024,
                    "upload_speed": 512,
                    "eta": 1800,
                },
                {
                    "id": 2,
                    "name": "Torrent 2",
                    "status": "seeding",
                    "progress": 100.0,
                    "download_speed": 0,
                    "upload_speed": 2048,
                    "eta": None,
                },
            ]
        }
        tlist = TorrentList.model_validate(data)
        assert len(tlist.torrents) == 2
        assert tlist.torrents[0].name == "Torrent 1"
        assert tlist.torrents[1].progress == 100.0


@pytest.mark.unit
class TestTorrentToModel:
    def test_converts_status_enum_to_string(self):
        fake = make_fake_torrent(status=FakeStatus.DOWNLOADING)
        result = _torrent_to_model(fake)
        assert result.status == "downloading"

    def test_handles_status_without_value_attr(self):
        fake = make_fake_torrent()
        fake.status = "some_string_status"
        result = _torrent_to_model(fake)
        assert result.status == "some_string_status"

    def test_handles_negative_eta(self):
        fake = make_fake_torrent(eta=-1)
        result = _torrent_to_model(fake)
        assert result.eta is None

    def test_handles_zero_eta(self):
        fake = make_fake_torrent(eta=0)
        result = _torrent_to_model(fake)
        assert result.eta is None

    def test_handles_none_eta(self):
        fake = make_fake_torrent(eta=None)
        result = _torrent_to_model(fake)
        assert result.eta is None

    def test_handles_positive_eta(self):
        fake = make_fake_torrent(eta=3600)
        result = _torrent_to_model(fake)
        assert result.eta == 3600

    def test_maps_rate_fields_correctly(self):
        fake = make_fake_torrent(rate_download=5000, rate_upload=2500)
        result = _torrent_to_model(fake)
        assert result.download_speed == 5000
        assert result.upload_speed == 2500

    def test_maps_all_fields(self):
        fake = make_fake_torrent(
            id=42,
            name="Test.Movie.2024.1080p",
            status=FakeStatus.SEEDING,
            progress=100.0,
            rate_download=0,
            rate_upload=1024,
            eta=-1,
        )
        result = _torrent_to_model(fake)
        assert result.id == 42
        assert result.name == "Test.Movie.2024.1080p"
        assert result.status == "seeding"
        assert result.progress == 100.0
        assert result.download_speed == 0
        assert result.upload_speed == 1024
        assert result.eta is None
