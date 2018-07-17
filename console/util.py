import xml.dom.minidom
import os
import json
from app import create_app
from app.main.models import Project, ProjectRelation, ProjectData
from app.manage.models import AttrContent, Attr
from app.main.func import get_project_children, get_project_children_v2
from collections import defaultdict, OrderedDict
from enum import Enum

app = create_app()
app.app_context().push()


class Byte(Enum):
    byte = 'BytePosition'


class Bite(Enum):
    bite = 'BitPosition'


class ExportXml(object):

    def __init__(self, project_id):
        self.project_id = project_id

    def set_path(self):
        path = os.path.abspath(os.path.dirname(__file__))
        real_path = os.path.join(path, 'files', 'all')
        files_path = os.path.join(real_path, '%s.xml' % self.xml_managers_attr)

        if not os.path.exists(real_path):
            os.makedirs(real_path)
        return files_path

    def set_dir_path(self, project_name):
        path = os.path.abspath(os.path.dirname(__file__))
        real_path = os.path.join(path, 'files', project_name)
        files_path = os.path.join(real_path, '%s.xml' % self.xml_managers_attr)

        if not os.path.exists(real_path):
            os.makedirs(real_path)
        return files_path

    @property
    def xml_managers_attr(self):
        project = Project.query.get_or_404(self.project_id)
        return project.name

    @staticmethod
    def __ecu_order():
        attr = Attr.query.filter_by(level=1).first()
        if not attr or not attr.content:
            return list()
        content = json.loads(attr.content)
        result = list()
        for c in content:
            if c.get('item_protocol'):
                result.append('%s-%s' % (c['item_protocol'], c['item']))
            else:
                result.append(c['item'])
        return result

    @property
    def xml_header_attr(self):
        result = OrderedDict()
        project_relation = ProjectRelation.query.filter_by(project_id=self.project_id, parent_id=None).first()

        if not project_relation:
            return result

        attr_content = AttrContent.query.filter_by(project_relation_id=project_relation.id).first()

        if not attr_content or not attr_content.real_content:
            return result

        content = json.loads(attr_content.real_content)

        order_content = self.__ecu_order()
        if order_content:
            for oc in order_content:
                result[oc] = content.get(oc)
        print('result:', dict(result))
        return dict(result)

    @property
    def xml_did_list(self):
        result = dict()
        project_relation = ProjectRelation.query.filter_by(project_id=self.project_id, level=2).all()
        if not project_relation:
            return result

        for pr in project_relation:
            attr_content = AttrContent.query.filter_by(project_relation_id=pr.id).first()
            real_content = json.loads(attr_content.real_content) if attr_content and attr_content.real_content else None
            result[pr.name] = real_content or {}

        return result

    @property
    def read_section(self):
        result = get_project_children(self.project_id)
        return list(set([v['level_2'] for v in result if v.get('level_2')]))

    def __get_(self, projects):
        d = defaultdict(list)

        project_relation_ids = [project['project_relation_id'] for project in projects if
                                project.get('project_relation_id')]

        attr_content = AttrContent.query.filter(AttrContent.project_relation_id.in_(project_relation_ids)).all()
        pro = ProjectRelation.query.filter(ProjectRelation.id.in_(project_relation_ids)).all()

        r = defaultdict(list)
        d['parameter_name'] = [{p.id: p.name} for p in pro]
        if attr_content:
            for ac in attr_content:
                content = json.loads(ac.real_content) if ac and ac.real_content else None
                if content:
                    r[ac.project_relation_id].append(content)
        d['byte'] = r
        return d

    @property
    def modification(self):
        r = defaultdict(list)
        result = get_project_children(self.project_id)
        if result:
            for v in result:
                r[v['level_2']].append({'project_relation_id': v['level_3_id']})

        new_result = dict()

        if r:
            for address, projects in r.items():
                project_query = ProjectData.query.filter_by(project_id=self.project_id)
                project = project_query.all()
                conf_data = defaultdict(list)
                for pro in project:
                    parent_relation = ProjectRelation.query.get_or_404(pro.project_relation_id)
                    conf_data[parent_relation.parent_id].append((pro.conf_data, pro.las))

                conf_data = {k: v for k, v in conf_data.items()}
                conf_data = {
                    'conf_data': conf_data
                }
                new_result[address] = dict(conf_data, **self.__get_(projects))

        return new_result

    def set_xml(self):
        doc = xml.dom.minidom.Document()
        root = doc.createElement('ConfigurationModule')

        root.setAttribute('%s-CONFIG-SCHEMA-VERSION' % self.xml_managers_attr, '1.0')
        doc.appendChild(root)

        # header
        manager_dict = self.xml_header_attr
        header_manager = doc.createElement('Header')
        if manager_dict:
            protocols = [{k.split('-')[0]: [k.split('-')[1], v]} for k, v in manager_dict.items() if '-' in k]
            new_protocols = defaultdict(list)
            for pt in protocols:
                for kkk, vvv in pt.items():
                    new_protocols[kkk].append(vvv)
            print(121, new_protocols)
            print(1, manager_dict)

            node_name_protocol = doc.createElement('Protocol')
            inter_val = True
            for key, val in manager_dict.items():
                if '-' in key and inter_val:
                    inter_val = False
                    for nk, nv in new_protocols.items():
                        node_protocol_k = doc.createElement(nk)
                        for nvv in nv:
                            node_protocol_k_name = doc.createElement(nvv[0])
                            node_protocol_k_name.appendChild(doc.createTextNode(str(nvv[1])))
                            node_protocol_k.appendChild(node_protocol_k_name)
                        node_name_protocol.appendChild(node_protocol_k)
                    header_manager.appendChild(node_name_protocol)

                else:
                    if '-' not in key:
                        node_name = doc.createElement(key)
                        node_name.appendChild(doc.createTextNode(str(val)))
                        header_manager.appendChild(node_name)
        root.appendChild(header_manager)

        # did list
        did_list = {k: v for k, v in self.xml_did_list.items() if v}
        node_did_list = doc.createElement('DidList')
        if did_list:
            for cid, val in did_list.items():
                node_did_item = doc.createElement('DidItem')
                for k, v in val.items():
                    did_item_s = doc.createElement(k)
                    did_item_s.appendChild(doc.createTextNode(str(v)))
                    node_did_item.appendChild(did_item_s)
                node_did_list.appendChild(node_did_item)
        root.appendChild(node_did_list)

        # ReadSection
        section_manager = doc.createElement('ReadSection')
        if self.read_section:
            for v in self.read_section:
                node_name = doc.createElement('ReadItem')
                node_name.setAttribute('IDREF', v)
                section_manager.appendChild(node_name)
        root.appendChild(section_manager)

        # ModificationSection
        modification_section = self.modification
        node_modification = doc.createElement('ModificationSection')
        if modification_section:
            for key, val in modification_section.items():
                node_modification_item = doc.createElement('ModificationItem')
                node_modification_item.setAttribute('IDREF', key)

                # ParameterName
                parameter_name = val['parameter_name']
                byte = dict(val['byte'])

                for parameter_val in parameter_name:
                    node_parameter = doc.createElement('Parameter')

                    try:
                        default_val = val['conf_data'].get(list(parameter_val.keys())[0])[0][0][0]
                    except Exception:
                        default_val = ''

                    node_parameter.setAttribute('ParamDefaultValue', default_val)
                    for parameter_k, parameter_v in parameter_val.items():
                        node_parameter_name = doc.createElement('ParameterName')
                        node_parameter_name.appendChild(doc.createTextNode(str(parameter_v)))
                        node_modification_item.appendChild(node_parameter_name)

                        byte_content = byte.get(parameter_k)

                        # bite
                        if byte_content:
                            for val_byte in byte_content:
                                for kk, vv in val_byte.items():
                                    node_byte_name = doc.createElement(kk)
                                    node_byte_name.appendChild(doc.createTextNode(str(vv)))
                                    node_modification_item.appendChild(node_byte_name)

                        # ConfData
                        node_conf_data = doc.createElement('ConfData')
                        node_conf_data.setAttribute('useConfData', 'true')

                        conf_data = val['conf_data'].get(parameter_k)
                        if conf_data:
                            for data in conf_data:
                                node_config_data = doc.createElement('ConfigData')
                                node_config_data.setAttribute('Value', data[0])

                                node_config_data.setAttribute('ConfigExpression', data[1])
                                node_conf_data.appendChild(node_config_data)

                                node_parameter.appendChild(node_conf_data)

                    node_modification_item.appendChild(node_parameter)
                node_modification.appendChild(node_modification_item)
        root.appendChild(node_modification)

        node_write_section = doc.createElement('WriteSection')
        if modification_section:
            for key, val in modification_section.items():
                node_write_item = doc.createElement('WriteItem')
                node_write_item.setAttribute('IDREF', key)
                node_write_item.setAttribute('DidWriteScope', 'All')
                node_write_item.setAttribute('DelayForMS', '0')
                node_write_section.appendChild(node_write_item)
        root.appendChild(node_write_section)

        return doc

    def run(self):
        files_path = self.set_path()
        doc = self.set_xml()
        fp = open(files_path, 'w', encoding='utf-8')
        doc.writexml(fp, indent='\t', addindent='\t', newl='\n', encoding="utf-8")

    def mk_dir(self, project_name):
        files_path = self.set_dir_path(project_name)
        doc = self.set_xml()
        fp = open(files_path, 'w', encoding='utf-8')
        doc.writexml(fp, indent='\t', addindent='\t', newl='\n', encoding="utf-8")


if __name__ == '__main__':
    export_xml = ExportXml(1)
    export_xml.run()
