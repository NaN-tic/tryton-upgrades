#!/usr/bin/env python
# -*- encoding: utf-8 -*-
import sys

dbname = sys.argv[1]
config_file = sys.argv[2]
from trytond.config import config as CONFIG
CONFIG.update_etc(config_file)

from trytond.pool import Pool
from trytond.transaction import Transaction
import logging

Pool.start()
pool = Pool(dbname)
pool.init()

context = {}

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

context['language'] = 'en'
with Transaction().start(dbname, 0, context=context) as transaction:
    pool = Pool()
    Status = pool.get('project.work.status')
    Tracker = pool.get('project.work.tracker')
    Field = pool.get('ir.model.field')

    cursor = transaction.connection.cursor()

    # reset values
    query = 'select id, name, galatea, sequence, invoiceable, role, comment from project_work_task_phase';
    cursor.execute(query)

    task_phases = {}
    phase2status = {}
    to_create = []
    to_write = []
    for row in cursor.fetchall():
        task_phases[row[0]] = row[1]
        # done
        if row[0] in [4]:
            status = Status(2)
            status.galatea = row[2]
            status.sequence = row[3]
            status.invoiceable = row[4]
            status.role = row[5]
            status.comment = row[6]
            status.types = ['project', 'task']
            status.save()
        else:
            status = Status()
            status.name = row[1]
            status.galatea = row[2]
            status.sequence = row[3]
            status.invoiceable = row[4]
            status.role = row[5]
            status.comment = row[6]
            status.types = ['project', 'task']

            trackers = []
            query = 'select tracker from "project_work_task_phase-project_work_tracker" where task_phase = %s' % (row[0]);
            cursor.execute(query)
            for row2 in cursor.fetchall():
                tracker = Tracker(row2[0])
                trackers.append(tracker)
            if trackers:
                status.required_effort = trackers
            status.save()

        phase2status[row[0]] = status.id

    query = 'select id, phase from project_work_workflow_line';
    cursor.execute(query)
    for row3 in cursor.fetchall():
        status_id = phase2status[row3[1]]
        query = 'UPDATE project_work_workflow_line set status = %s where id = %s' % (status_id, row3[0]);
        cursor.execute(query)

    status = dict((x.name, x.id) for x in Status.search([]))
    for phase_id, phase_name in task_phases.items():
        if phase_name == 'Finished':
            phase_name = 'Done'
        status_id = status[phase_name]
        query = 'UPDATE project_work set status = %s where task_phase = %s' % (status_id, phase_id);
        cursor.execute(query)
    transaction.commit()

# locales
for lang in ('ca', 'es'):
    context['language'] = lang
    with Transaction().start(dbname, 0, context=context) as transaction:
        pool = Pool()
        Status = pool.get('project.work.status')
        Tracker = pool.get('project.work.tracker')
        Field = pool.get('ir.model.field')

        cursor = transaction.connection.cursor()

        # reset values
        query = 'select id, name, galatea, sequence, invoiceable, role, comment from project_work_task_phase';
        cursor.execute(query)

        to_write = []
        for row4 in cursor.fetchall():
            if row4[0] in [4]:
                continue
            status_id = phase2status[row4[0]]
            query = "select id, src, value, name res_id from ir_translation where name = 'project.work.task_phase,name' and res_id = %s and lang = '%s'" % (row4[0], lang);
            cursor.execute(query)
            vals = cursor.fetchone()
            if vals:
                status = Status(status_id)
                status.name = vals[2]
                status.save()

        transaction.commit()

logger.info('Done')
