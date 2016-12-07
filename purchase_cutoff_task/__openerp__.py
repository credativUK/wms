# -*- coding: utf-8 -*-
# (c) 2016 credativ ltd. - Ondřej Kuzník
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

{
    'name': 'Enable purchase cutoff',
    'version': '7.20161020.0',
    'category': 'Purchase',
    'author': 'credativ ltd.',
    'license': 'AGPL-3',
    'depends': [
        'connector_prism',
        'queue_tasks',
    ],
    'data': [
        'views/purchase_view.xml',
    ],
}
