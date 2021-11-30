# -*- encoding: utf-8 -*-
#!/usr/bin/env python
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
    to_create = []
    to_write = []
    for row in cursor.fetchall():
        task_phases[row[0]] = row[1]
        # done
        if row[0] in [4]:
            status = Status(2)
            to_write.extend(([status], {
                'galatea': row[2],
                'sequence': row[3],
                'invoiceable': row[4],
                'role': row[5],
                'comment': row[6],
            }))
        else:
            status = Status()
            status.name = row[1]
            status.galatea = row[2]
            status.sequence = row[3]
            status.invoiceable = row[4]
            status.role = row[5]
            status.comment = row[6]

            trackers = []
            query = 'select tracker from "project_work_task_phase-project_work_tracker" where task_phase = %s' % (row[0]);
            cursor.execute(query)
            for row2 in cursor.fetchall():
                tracker = Tracker(row2[0])
                trackers.append(tracker)
            if trackers:
                status.required_effort = trackers

            # required_fields = []
            # query = 'select field from "project_task_phase-required_fields" where phase = %s' % (row[0]);
            # cursor.execute(query)
            # for row3 in cursor.fetchall():
            #     field = Field(row3[0])
            #     required_fields.append(field)
            # if required_fields:
            #     status.required_fields = required_fields

            to_create.append(status._save_values)

    if to_create:
        Status.create(to_create)
    if to_write:
        Status.write(*to_write)

    status = dict((x.name, x.id) for x in Status.search([]))
    for phase_id, phase_name in task_phases.items():
        if phase_name == 'Finished':
            phase_name = 'Done'
        status_id = status[phase_name]
        query = 'UPDATE project_work set status = %s where task_phase = %s' % (status_id, phase_id);
        cursor.execute(query)
    transaction.commit()
    logger.info('Done')
