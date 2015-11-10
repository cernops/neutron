#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import sqlalchemy as sa
from sqlalchemy import orm
from sqlalchemy.orm import exc as orm_exc
from oslo.db import exception as db_exc

from neutron.db import common_db_mixin
from neutron.db import model_base
from neutron.db import models_v2
from oslo_log import log as logging
from neutron.openstack.common import uuidutils
from neutron.extensions import subnetcluster
from neutron.plugins.ml2 import cern


LOG = logging.getLogger(__name__)


class Cluster(model_base.BASEV2, models_v2.HasId, models_v2.HasTenant):

    __tablename__ = 'cern_clusters'

    name = sa.Column(sa.String(255), unique=True, nullable=False)


class SubnetCluster(model_base.BASEV2):

    __tablename__ = 'cern_subnet_clusters'

    subnet_id = sa.Column(sa.String(36),
                          sa.ForeignKey('subnets.id'),
                          primary_key=True, unique=True)
    cluster_id = sa.Column(sa.String(36),
                           sa.ForeignKey('cern_clusters.id'),
                           primary_key=True)

    subnets = orm.relationship(
        models_v2.Subnet,
        backref=orm.backref("cluster", lazy='joined',
                            cascade="all, delete-orphan", uselist=False))

    cluster = orm.relationship(
        Cluster,
        backref=orm.backref("subnets", lazy='joined', 
                            cascade="all, delete-orphan", uselist=True))


class SubnetClusterDbMixin(subnetcluster.SubnetClusterPluginBase, 
                           common_db_mixin.CommonDbMixin):
    """Mixin class to add subnetcluster extension to db_plugin_base_v2."""

    def _get_cluster(self, context, id):
        try:
            cluster = self._get_by_id(context, Cluster, id)
        except orm_exc.NoResultFound:
            raise subnetcluster.ClusterNotFound(cluster_id=id)
        return cluster

    def _make_cluster_dict(self, cluster, fields=None):
        res = {'id': cluster['id'],
               'name': cluster['name'],
               'subnets': []}

        for subnet in cluster['subnets']:
            res['subnets'].append(subnet['subnet_id'])

        return self._fields(res, fields)

    def get_cluster(self, context, id, fields=None):
        cluster = self._get_cluster(context, id)
        return self._make_cluster_dict(cluster, fields)

    def get_clusters(self, context, filters=None, fields=None):
        return self._get_collection(context, Cluster,
                                    self._make_cluster_dict,
                                    filters=filters, fields=fields)

    def get_clusters_count(self, context, filters=None):
        return self._get_collection_count(context, Cluster,
                                          filters=filters)

    def create_cluster(self, context, cluster):
        cluster_data = cluster['cluster']
        try:
            with context.session.begin(subtransactions=True):
                record = Cluster(
                    id=uuidutils.generate_uuid(),
                    name=cluster_data['name']
                )
                context.session.add(record) 
                return self._make_cluster_dict(record)
        except db_exc.DBDuplicateEntry:
            raise subnetcluster.ClusterExists(name=cluster_data['name'])

    def update_cluster(self, context, id, cluster):
        cluster_data = cluster['cluster']
        try:
            with context.session.begin(subtransactions=True):
                cluster = self._get_cluster(context, id)
                cluster.update(cluster_data)
            return self._make_cluster_dict(cluster)
        except db_exc.DBDuplicateEntry:
            raise subnetcluster.ClusterExists(name=cluster_data['name'])

    def delete_cluster(self, context, id):
        with context.session.begin(subtransactions=True):
            cluster = self._get_cluster(context, id)
            context.session.delete(cluster)

    def insert_subnet(self, context, id, body):
        try:
            with context.session.begin(subtransactions=True):
                record = SubnetCluster(
                    subnet_id=body['cluster']['subnet_id'],
                    cluster_id=id
                )
                context.session.add(record)
        except db_exc.DBDuplicateEntry:
            raise subnetcluster.SubnetInOtherCluster(subnet=body['cluster']['subnet_id'])
        except db_exc.DBError:
            raise subnetcluster.SubnetAlreadyInCluster(cluster=id, subnet=body['cluster']['subnet_id'])

    def remove_subnet(self, context, id, body):
        try:
            with context.session.begin(subtransactions=True):
                query = self._model_query(context, SubnetCluster)
                record = query.filter(
                    SubnetCluster.cluster_id == id,
                    SubnetCluster.subnet_id == body['cluster']['subnet_id']).one()
                context.session.delete(record)
        except orm_exc.NoResultFound:
            raise subnetcluster.SubnetNotInCluster(cluster=id, 
                                                   subnet=body['cluster']['subnet_id'])

    def get_cluster_by_subnet(self, context, id):
        clusters_query = context.session.query(SubnetCluster)
        cluster_id = clusters_query.filter(SubnetCluster.subnet_id == id)[0]['cluster_id']
        return self.get_cluster(context, cluster_id)

    def get_cluster_by_name(self, context, name):
        clusters_query = context.session.query(Cluster)
        cluster = clusters_query.filter(Cluster.name == name).first()
        if cluster is not None:
            cluster_id = cluster['id']
            return self.get_cluster(context, cluster_id)
        else:
            return None
