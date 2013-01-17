# -*- coding: utf-8 -*-

import json
import logging
import unittest
from mock import patch

from nailgun.settings import settings
from nailgun.test.base import BaseHandlers
from nailgun.test.base import reverse
from nailgun.network import manager as netmanager
from nailgun.api.models import Cluster


class TestProvisioning(BaseHandlers):

    @patch('nailgun.rpc.cast')
    def test_nodes_in_cluster(self, mocked_rpc):
        cluster = self.create_cluster_api()
        node = self.create_default_node()
        node2 = self.create_default_node()
        node2.status = "discover"
        node2.pending_addition = True
        node3 = self.create_default_node()
        cluster_db = self.db.query(Cluster).get(cluster['id'])
        cluster_db.nodes.append(node)
        cluster_db.nodes.append(node2)
        self.db.add(cluster_db)
        self.db.commit()

        self.assertEqual(len(cluster_db.nodes), 2)

        netmanager.assign_ips = self.mock.MagicMock()

        with patch('nailgun.task.task.Cobbler'):
            resp = self.app.put(
                reverse(
                    'ClusterChangesHandler',
                    kwargs={"cluster_id": cluster['id']}),
                "",
                headers=self.default_headers
            )
            self.assertEquals(200, resp.status)

    @patch('nailgun.rpc.cast')
    def test_node_status_changes_to_provision(self, mocked_rpc):
        cluster = self.create_cluster_api()
        node_ready = self.create_default_node(cluster_id=cluster['id'],
                                              status='ready',
                                              pending_addition=True)
        node_discover = self.create_default_node(cluster_id=cluster['id'],
                                                 status='discover',
                                                 pending_addition=True)
        node_provis = self.create_default_node(cluster_id=cluster['id'],
                                               status='provisioning',
                                               pending_addition=True)
        node_deploy = self.create_default_node(cluster_id=cluster['id'],
                                               status='deploying',
                                               pending_addition=True)
        node_error_deploy = self.create_default_node(cluster_id=cluster['id'],
                                                     status='error',
                                                     error_type='deploy')
        node_error_provis = self.create_default_node(cluster_id=cluster['id'],
                                                     status='error',
                                                     error_type='provision')

        netmanager.assign_ips = self.mock.MagicMock()

        with patch('nailgun.task.task.Cobbler'):
            resp = self.app.put(
                reverse(
                    'ClusterChangesHandler',
                    kwargs={"cluster_id": cluster['id']}),
                "",
                headers=self.default_headers
            )
            self.assertEquals(200, resp.status)

        for n in (node_ready, node_discover, node_provis, node_deploy,
                  node_error_deploy, node_error_provis):
            self.db.refresh(n)

        self.assertEquals(node_ready.status, 'provisioned')
        self.assertEquals(node_discover.status, 'provisioning')
        self.assertEquals(node_provis.status, 'provisioning')
        self.assertEquals(node_deploy.status, 'provisioned')
        self.assertEquals(node_error_deploy.status, 'error')
        self.assertEquals(node_error_provis.status, 'provisioning')
