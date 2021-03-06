from . import main
from flask import jsonify, request
from flask_login import login_required, current_user
# from .models import *
from .func import *
from ..manage.models import *
import json


@main.route('/project/func/tree')
@login_required
def get_prject_func_tree():
    result = {
        'nodedata': [],
        'linkdata': [],
    }

    project_id = request.args.get('project_id')
    parent_id = request.args.get('id')
    level = request.args.get('level') or 0
    print(level)
    if level and int(level) < 3:
        return jsonify({'success': True, 'data': result})

    if not project_id or not parent_id:
        return jsonify({'success': False, 'messgae': 'id 不存在'})

    result = get_func_relation(result, project_id, parent_id)
    return jsonify({'success': True, 'data': result})


# project tree
@main.route('/project/tree')
@login_required
def get_project_tree():
    result = {
        'nodedata': [],
        'linkdata': [],
    }

    project_id = request.args.get('project_id')
    if not project_id:
        return jsonify({'success': False, 'message': '没有获取到配置文件信息'})

    project_relations_query = ProjectRelation.query.order_by(ProjectRelation.relation_order, ProjectRelation.id)
    project_relations = project_relations_query.filter_by(project_id=project_id, type='worker').all()

    if not project_relations:
        return jsonify({'success': True, 'data': result})

    link_data = []
    for relation in project_relations:
        if relation.parent_id:
            link_data.append({'from': relation.parent_id, 'to': relation.id})

        result['nodedata'].append({
            'name': relation.name,
            'key': relation.id,
            'level': relation.level,
            'category': 'FirstNode' if relation.level == 1 else ('SecondNode' if relation.level == 2 else 'ThirdNode')
        })

    result['linkdata'] = link_data
    return jsonify({'success': True, 'data': result})


# project edit
@main.route('/project/create', methods=['POST'])
@login_required
def create_project():
    form_data = request.form.to_dict()
    if not form_data.get('name'):
        return jsonify({'success': False, 'message': '项目名称不能为空'})

    project = Project.query.filter_by(name=form_data['name']).first()
    if project:
        return jsonify({'success': False, 'message': '项目名称重复'})

    d = {
        'name': form_data['name'],
        'user_id': current_user.get_id(),
    }

    add_project = Project(**d)
    db.session.add(add_project)
    db.session.flush()

    project_id = add_project.id

    project_relation = {
        'name': form_data['name'],
        'project_id': project_id
    }

    relation = ProjectRelation(**project_relation)
    db.session.add(relation)
    return jsonify({'success': True, 'message': '更新成功', 'project_id': project_id})


@main.route('/project/content/add/<int:id>', methods=['POST'])
@login_required
def add_file_tree_content(id):
    form_data = request.form.to_dict()
    copy_id = request.args.get('copy_id')
    action = request.args.get('action')

    copy_parent_id = get_copy_parent_id(copy_id)
    if isinstance(copy_parent_id, dict):
        return jsonify(copy_parent_id)

    if not form_data.get('content'):
        return jsonify({'success': False, 'message': '内容不能为空'})

    d = {
        'parent_id': form_data.get('parent_id') if not copy_parent_id else copy_parent_id,
        'project_id': id,
        'level': form_data.get('level'),
    }

    print(form_data.get('level'))
    if form_data.get('level') == '4':
        d['type'] = 'func'

    copy_result_id = ProjectRelation.add_project_relation(d, form_data['content'], id)
    if copy_result_id and action == 'copy':
        copy_product_children(copy_id, copy_result_id)
    return jsonify({'success': True, 'type': form_data.get('type')})


@main.route('/project/tree/delete/<int:id>', methods=['POST'])
@login_required
def delete_project_tree(id):
    project_relation = ProjectRelation.query.filter_by(id=id).first()
    if not project_relation:
        return jsonify({'success': False, 'message': '没有此记录'})
    if not project_relation.parent_id:
        return jsonify({'success': False, 'message': '这节点为根节点，不支持删除'})

    parent_id = project_relation.parent_id
    db.session.delete(project_relation)
    delete_project_children(id)
    order_delete_project(parent_id)
    return jsonify({'success': True, 'message': '更新成功'})


@main.route('/project/delete/<int:id>', methods=['POST'])
@login_required
def delete_project(id):
    project = Project.query.get_or_404(id)
    db.session.delete(project)
    return jsonify({'success': True, 'message': '删除成功'})


@main.route('/project/relation', methods=['POST'])
@login_required
def update_project_relation_order():
    id = request.args.get('id')

    type = request.args.get('type')
    if not id or not type:
        return jsonify({'success': False, 'message': '参数不对'})

    project_relation = ProjectRelation.query.filter_by(id=id).first()
    if not project_relation:
        return jsonify({'success': False, 'message': '没有记录'})
    parent_id = project_relation.parent_id

    if type == 'up':
        prev_project_relation = ProjectRelation.query.filter_by(parent_id=parent_id,
                                                                relation_order=project_relation.relation_order - 1).first()
        if not prev_project_relation:
            return jsonify({'success': False, 'message': '不能上移'})

        pre_order = prev_project_relation.relation_order + 1
        this_order = prev_project_relation.relation_order

        prev_project_relation.relation_order = pre_order
        project_relation.relation_order = this_order

        return jsonify({'success': True, 'message': '更新成功'})

    else:
        next_project_relation = ProjectRelation.query.filter_by(parent_id=parent_id,
                                                                relation_order=project_relation.relation_order + 1).first()
        if not next_project_relation:
            return jsonify({'success': False, 'message': '不能下移'})

        next_order = next_project_relation.relation_order - 1
        this_order = next_project_relation.relation_order

        next_project_relation.relation_order = next_order
        project_relation.relation_order = this_order

        return jsonify({'success': True, 'message': '更新成功'})


# main attr content
@main.route('/attr/content', methods=['GET', 'POST'])
@login_required
def submit_attr_content():
    # get attr 参数
    level = request.args.get('level')
    project_id = request.args.get('project_id')
    project_relation_id = request.args.get('project_relation_id')

    attr = Attr.query.filter(Attr.level == level).first()

    if not attr or not project_id or not project_relation_id:
        return jsonify({'success': False, 'messgae': '参数不对'})

    data = None
    content = None
    if attr.content:
        data = json.loads(attr.content)

    attr_content = AttrContent.query.filter_by(project_id=project_id, project_relation_id=project_relation_id).first()

    if attr_content and attr_content.real_content:
        content = json.loads(attr_content.real_content)
    return jsonify({'success': True, 'data': data, 'content': content})
