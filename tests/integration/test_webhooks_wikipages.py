# -*- coding: utf-8 -*-
# Copyright (C) 2014-2017 Andrey Antukh <niwi@niwi.nz>
# Copyright (C) 2014-2017 Jesús Espino <jespinog@gmail.com>
# Copyright (C) 2014-2017 David Barragán <bameda@dbarragan.com>
# Copyright (C) 2014-2017 Alejandro Alonso <alejandro.alonso@kaleidos.net>
# Copyright (C) 2014-2017 Anler Hernández <hello@anler.me>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import pytest
from unittest.mock import patch
from unittest.mock import Mock

from .. import factories as f

from taiga.projects.history import services


pytestmark = pytest.mark.django_db(transaction=True)


from taiga.base.utils import json

def test_webhooks_when_create_wiki_page(settings):
    settings.WEBHOOKS_ENABLED = True
    project = f.ProjectFactory()
    f.WebhookFactory.create(project=project)
    f.WebhookFactory.create(project=project)

    obj = f.WikiPageFactory.create(project=project)

    with patch('taiga.webhooks.tasks._send_request') as send_request_mock:
        services.take_snapshot(obj, user=obj.owner)
        assert send_request_mock.call_count == 2

        (webhook_id, url, key, data) = send_request_mock.call_args[0]
        assert data["action"] == "create"
        assert data["type"] == "wikipage"
        assert data["by"]["id"] == obj.owner.id
        assert "date" in data
        assert data["data"]["id"] == obj.id


def test_webhooks_when_update_wiki_page(settings):
    settings.WEBHOOKS_ENABLED = True
    project = f.ProjectFactory()
    f.WebhookFactory.create(project=project)
    f.WebhookFactory.create(project=project)

    obj = f.WikiPageFactory.create(project=project)

    with patch('taiga.webhooks.tasks._send_request') as send_request_mock:
        services.take_snapshot(obj, user=obj.owner)
        assert send_request_mock.call_count == 2

    obj.content = "test webhook update"
    obj.save()

    with patch('taiga.webhooks.tasks._send_request') as send_request_mock:
        services.take_snapshot(obj, user=obj.owner, comment="test_comment")
        assert send_request_mock.call_count == 2

        (webhook_id, url, key, data) = send_request_mock.call_args[0]
        assert data["action"] == "change"
        assert data["type"] == "wikipage"
        assert data["by"]["id"] == obj.owner.id
        assert "date" in data
        assert data["data"]["id"] == obj.id
        assert data["data"]["content"] == obj.content
        assert data["change"]["comment"] == "test_comment"
        assert data["change"]["diff"]["content_html"]["from"] != data["change"]["diff"]["content_html"]["to"]
        assert obj.content in data["change"]["diff"]["content_html"]["to"]


def test_webhooks_when_delete_wiki_page(settings):
    settings.WEBHOOKS_ENABLED = True
    project = f.ProjectFactory()
    f.WebhookFactory.create(project=project)
    f.WebhookFactory.create(project=project)

    obj = f.WikiPageFactory.create(project=project)

    with patch('taiga.webhooks.tasks._send_request') as send_request_mock:
        services.take_snapshot(obj, user=obj.owner, delete=True)
        assert send_request_mock.call_count == 2

        (webhook_id, url, key, data) = send_request_mock.call_args[0]
        assert data["action"] == "delete"
        assert data["type"] == "wikipage"
        assert data["by"]["id"] == obj.owner.id
        assert "date" in data
        assert "data" in data


def test_webhooks_when_update_wiki_page_attachments(settings):
    settings.WEBHOOKS_ENABLED = True
    project = f.ProjectFactory()
    f.WebhookFactory.create(project=project)
    f.WebhookFactory.create(project=project)

    obj = f.WikiPageFactory.create(project=project)

    with patch('taiga.webhooks.tasks._send_request') as send_request_mock:
        services.take_snapshot(obj, user=obj.owner)
        assert send_request_mock.call_count == 2

    # Create attachments
    attachment1 = f.WikiAttachmentFactory(project=obj.project, content_object=obj, owner=obj.owner)
    attachment2 = f.WikiAttachmentFactory(project=obj.project, content_object=obj, owner=obj.owner)

    with patch('taiga.webhooks.tasks._send_request') as send_request_mock:
        services.take_snapshot(obj, user=obj.owner, comment="test_comment")
        assert send_request_mock.call_count == 2

        (webhook_id, url, key, data) = send_request_mock.call_args[0]
        assert data["action"] == "change"
        assert data["type"] == "wikipage"
        assert data["by"]["id"] == obj.owner.id
        assert "date" in data
        assert data["data"]["id"] == obj.id
        assert data["change"]["comment"] == "test_comment"
        assert len(data["change"]["diff"]["attachments"]["new"]) == 2
        assert len(data["change"]["diff"]["attachments"]["changed"]) == 0
        assert len(data["change"]["diff"]["attachments"]["deleted"]) == 0

    # Update attachment
    attachment1.description = "new attachment description"
    attachment1.save()

    with patch('taiga.webhooks.tasks._send_request') as send_request_mock:
        services.take_snapshot(obj, user=obj.owner, comment="test_comment")
        assert send_request_mock.call_count == 2

        (webhook_id, url, key, data) = send_request_mock.call_args[0]
        assert data["action"] == "change"
        assert data["type"] == "wikipage"
        assert data["by"]["id"] == obj.owner.id
        assert "date" in data
        assert data["data"]["id"] == obj.id
        assert data["change"]["comment"] == "test_comment"
        assert len(data["change"]["diff"]["attachments"]["new"]) == 0
        assert len(data["change"]["diff"]["attachments"]["changed"]) == 1
        assert len(data["change"]["diff"]["attachments"]["deleted"]) == 0

    # Delete attachment
    attachment2.delete()

    with patch('taiga.webhooks.tasks._send_request') as send_request_mock:
        services.take_snapshot(obj, user=obj.owner, comment="test_comment")
        assert send_request_mock.call_count == 2

        (webhook_id, url, key, data) = send_request_mock.call_args[0]
        assert data["action"] == "change"
        assert data["type"] == "wikipage"
        assert data["by"]["id"] == obj.owner.id
        assert "date" in data
        assert data["data"]["id"] == obj.id
        assert data["change"]["comment"] == "test_comment"
        assert len(data["change"]["diff"]["attachments"]["new"]) == 0
        assert len(data["change"]["diff"]["attachments"]["changed"]) == 0
        assert len(data["change"]["diff"]["attachments"]["deleted"]) == 1
