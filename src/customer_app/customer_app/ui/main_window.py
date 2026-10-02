"""Functional V1 desktop shell for customers, jobs and field configuration."""
from __future__ import annotations

import csv
from datetime import date
from decimal import Decimal

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QFileDialog, QHBoxLayout,
    QHeaderView, QLabel, QLineEdit, QMainWindow, QMessageBox, QPushButton, QSplitter,
    QTableWidget, QTableWidgetItem, QTabWidget, QTreeWidget, QTreeWidgetItem,
    QVBoxLayout, QWidget, QAbstractItemView)

from ..backup import DatabaseBackupManager
from ..config import CORE_FIELDS, JOB_STATUSES, SettingsStore
from ..database import CustomerDatabase
from ..models import ValidationError, money_text
from ..paths import default_backup_dir
from .field_settings import FieldSettingsPage
from .forms import CustomerDialog, JobDialog


def display(value, kind='text'):
    if value is None: return ''
    if kind == 'currency': return '' if value == '' else '$' + f'{Decimal(str(value)):,.2f}'
    if isinstance(value,list): return ', '.join(value)
    if isinstance(value,bool): return 'Yes' if value else 'No'
    if kind == 'date' and value:
        try: return date.fromisoformat(value).strftime('%d/%m/%Y')
        except ValueError: pass
    return str(value)

class CustomerMainWindow(QMainWindow):
    def __init__(self, *, db=None, settings_store=None, enable_backups=True):
        super().__init__()
        self.store = settings_store or SettingsStore()
        self.settings = self.store.load()
        self.db = db or CustomerDatabase(self.settings.db_path,self.settings)
        self.db.settings = self.settings
        self.selected_customer = None
        self.backup_manager = DatabaseBackupManager(self.db.db_path,default_backup_dir(),self.db.key_hex) if enable_backups else None
        self.setWindowTitle('ShiningKnights | Customers & Jobs')
        self.resize(1250,820)
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        self._home_page()
        self._customer_page()
        self._jobs_page()
        self.configuration = FieldSettingsPage(self.settings,self.store)
        self.configuration.settings_saved.connect(self.apply_settings)
        self.tabs.addTab(self.configuration,'Field settings')
        self.refresh_all()
        self.backup_timer = QTimer(self)
        self.backup_timer.timeout.connect(self.automatic_backup)
        if self.backup_manager:
            self.backup_timer.start(60 * 60 * 1000)
            self.automatic_backup()
        self.statusBar().showMessage('Encrypted customer and job database ready')

    def _button(self, label, handler):
        b = QPushButton(label); b.clicked.connect(handler); return b

    def _home_page(self):
        self.home = QWidget(); l = QVBoxLayout(self.home)
        title = QLabel('Customers & jobs'); title.setObjectName('title'); l.addWidget(title)
        self.metrics = QLabel(); self.metrics.setObjectName('metrics'); self.metrics.setWordWrap(True); l.addWidget(self.metrics)
        row = QHBoxLayout()
        row.addWidget(self._button('Add customer',self.add_customer))
        row.addWidget(self._button('Add job',self.add_job))
        row.addWidget(self._button('Back up now',self.manual_backup))
        row.addStretch(); l.addLayout(row)
        l.addWidget(QLabel('Customers due for service\nBased on last completed visit and frequency. Scheduled visits are shown separately.'))
        self.due_table = QTableWidget(); self._setup_table(self.due_table)
        self.due_table.setColumnCount(4); self.due_table.setHorizontalHeaderLabels(['Customer','Suburb','Next due','Next scheduled'])
        self.due_table.cellDoubleClicked.connect(self.open_due_customer)
        l.addWidget(self.due_table)
        self.backup_label = QLabel(); self.backup_label.setWordWrap(True); l.addWidget(self.backup_label)
        l.addWidget(QLabel('Database: ' + str(self.db.db_path)))
        self.tabs.addTab(self.home,'Home')

    @staticmethod
    def _setup_table(table):
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setStretchLastSection(True)
        table.verticalHeader().setVisible(False)
        table.setAlternatingRowColors(True)

    def _customer_page(self):
        page = QWidget(); l = QVBoxLayout(page)
        row = QHBoxLayout()
        self.customer_search = QLineEdit(); self.customer_search.setPlaceholderText('Search name, address, phone, service or notes…')
        self.customer_search.textChanged.connect(self.refresh_customers)
        self.inactive = QCheckBox('Include inactive'); self.inactive.toggled.connect(self.refresh_customers)
        row.addWidget(self.customer_search); row.addWidget(self.inactive)
        row.addWidget(self._button('Add customer',self.add_customer)); row.addWidget(self._button('Export CSV',self.export_customers)); l.addLayout(row)
        splitter = QSplitter(Qt.Orientation.Vertical)
        self.customer_table = QTableWidget(); self._setup_table(self.customer_table)
        self.customer_table.itemSelectionChanged.connect(self.show_selected_customer)
        self.customer_table.cellDoubleClicked.connect(lambda *_:self.edit_customer())
        splitter.addWidget(self.customer_table)
        details = QWidget(); d = QVBoxLayout(details)
        self.profile = QLabel('Select a customer to see their service history.'); self.profile.setTextFormat(Qt.TextFormat.PlainText); self.profile.setWordWrap(True); d.addWidget(self.profile)
        buttons = QHBoxLayout()
        buttons.addWidget(self._button('Edit customer',self.edit_customer))
        buttons.addWidget(self._button('Add job for customer',lambda:self.add_job(self.selected_customer)))
        buttons.addWidget(self._button('Activate / deactivate',self.toggle_customer))
        buttons.addStretch(); d.addLayout(buttons)
        self.history = QTableWidget(); self._setup_table(self.history)
        self.history.cellDoubleClicked.connect(self.edit_history_job)
        d.addWidget(self.history); splitter.addWidget(details)
        splitter.setSizes([360,300]); l.addWidget(splitter)
        self.tabs.addTab(page,'Customers')

    def _jobs_page(self):
        page = QWidget(); l = QVBoxLayout(page)
        row = QHBoxLayout()
        self.job_search = QLineEdit(); self.job_search.setPlaceholderText('Search jobs or customers…'); self.job_search.textChanged.connect(self.refresh_jobs)
        self.job_filter = QComboBox(); self.job_filter.addItems(['All','Upcoming','Overdue',*JOB_STATUSES,'Trash']); self.job_filter.currentTextChanged.connect(self.refresh_jobs)
        self.group_by = QComboBox()
        for label,key in [('Group by date','date'),('Group by customer','customer'),('Group by status','status')]: self.group_by.addItem(label,key)
        self.group_by.currentIndexChanged.connect(self.refresh_jobs)
        row.addWidget(self.job_search); row.addWidget(self.job_filter); row.addWidget(self.group_by)
        row.addWidget(self._button('Add job',self.add_job)); row.addWidget(self._button('Export CSV',self.export_jobs)); l.addLayout(row)
        self.jobs_tree = QTreeWidget(); self.jobs_tree.setRootIsDecorated(True); self.jobs_tree.setAlternatingRowColors(True)
        self.jobs_tree.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.jobs_tree.itemDoubleClicked.connect(lambda *_:self.edit_job())
        l.addWidget(self.jobs_tree)
        row = QHBoxLayout()
        for label,fn in [('Edit job',self.edit_job),('Mark completed',self.mark_completed),('Move to Trash',self.trash_job),('Restore job',self.restore_job)]: row.addWidget(self._button(label,fn))
        row.addStretch(); l.addLayout(row)
        self.tabs.addTab(page,'Jobs')

    def _columns(self, entity):
        return [f for f in self.settings.fields_for(entity) if f.enabled and f.browse_column]

    def _field_value(self, record, f, entity):
        value = record.get(f.key) if f.key in CORE_FIELDS[entity] else record.get('custom_fields',{}).get(f.key)
        return display(value,f.field_type)

    def _fill_table(self, table, records, entity, extra=None):
        cols = self._columns(entity)
        headers = [f.label for f in cols]
        if extra: headers = [*headers,*extra.keys()]
        if not headers: headers = ['ID']
        table.setColumnCount(len(headers)); table.setHorizontalHeaderLabels(headers); table.setRowCount(len(records))
        for row,record in enumerate(records):
            values = [self._field_value(record,f,entity) for f in cols]
            if extra: values += [fn(record) for fn in extra.values()]
            if not values: values = [str(record['id'])]
            for col,value in enumerate(values):
                item = QTableWidgetItem(str(value)); item.setData(Qt.ItemDataRole.UserRole,record['id']); table.setItem(row,col,item)

    def refresh_customers(self):
        selected = self.selected_customer
        self.customer_rows = self.db.list_customers(self.customer_search.text(),include_inactive=self.inactive.isChecked())
        self.customer_table.blockSignals(True)
        summaries = {c['id']:self.db.customer_summary(c['id']) for c in self.customer_rows}
        self._fill_table(self.customer_table,self.customer_rows,'customers',{'Frequency':lambda c:self.frequency_text(c),'Completed jobs':lambda c:str(summaries[c['id']]['jobs_completed']),'Next due':lambda c:display(summaries[c['id']]['next_due'],'date')})
        self.customer_table.clearSelection()
        self.selected_customer = None
        for row,c in enumerate(self.customer_rows):
            if c['id'] == selected:
                self.customer_table.selectRow(row); self.selected_customer = selected; break
        self.customer_table.blockSignals(False)
        self.show_selected_customer()

    @staticmethod
    def frequency_text(c):
        return f"Every {c['frequency_value']} {c['frequency_unit']}" if c['frequency_value'] else 'One-off / as needed'

    def show_selected_customer(self):
        items = self.customer_table.selectedItems()
        self.selected_customer = items[0].data(Qt.ItemDataRole.UserRole) if items else None
        if self.selected_customer is None:
            self.profile.setText('Select a customer to see their service history.'); self.history.setRowCount(0); return
        c = self.db.get_customer(self.selected_customer); s = self.db.customer_summary(c['id'])
        address = ', '.join(v for v in (c['address_line_1'],c['address_line_2'],c['suburb'],c['state'],c['postcode']) if v)
        self.profile.setText(f"{c['name']}" + (' | Inactive' if not c['active'] else '') + f"\n{address}\n{c['phone']}  {c['email']}\n{self.frequency_text(c)} | {c['default_job_type']} | Standard fee: {display(c['default_fee'],'currency') or 'Not set'}\nEquipment: {display(c['default_equipment']) or 'Not set'} | Usual payment: {c['default_payment_type'] or 'Not set'}\nCompleted jobs: {s['jobs_completed']} | Last completed: {display(s['last_job'],'date') or 'None'} | Next due: {display(s['next_due'],'date') or 'Not set'} | Scheduled: {display(s['next_scheduled'],'date') or 'None'}\n{c['notes']}")
        self._fill_table(self.history,self.db.list_jobs(c['id']),'jobs')

    def _filtered_jobs(self):
        label = self.job_filter.currentText()
        jobs = self.db.list_jobs(status=label if label in JOB_STATUSES else '',include_deleted=label == 'Trash',group_by=self.group_by.currentData(),search=self.job_search.text())
        if label == 'Trash': jobs = [j for j in jobs if j['deleted_at']]
        if label in ('Upcoming','Overdue'): jobs = [j for j in jobs if j['status'] in ('Scheduled','In progress')]
        if label == 'Overdue': jobs = [j for j in jobs if j['scheduled_date'] and j['scheduled_date'] < date.today().isoformat()]
        return jobs

    def refresh_jobs(self):
        self.jobs_tree.clear()
        cols = self._columns('jobs')
        self.jobs_tree.setColumnCount(1+len(cols)); self.jobs_tree.setHeaderLabels(['Customer',*[f.label for f in cols]])
        self.job_rows = self._filtered_jobs()
        groups = {}
        key = self.group_by.currentData()
        for j in self.job_rows:
            label = j['customer_name'] if key == 'customer' else j['status'] if key == 'status' else display(j['scheduled_date'] or j['completed_date'],'date') or 'Unscheduled'
            # IDs separate two customers with the same display name.
            bucket = (j['customer_id'],label) if key == 'customer' else label
            if bucket not in groups:
                group = QTreeWidgetItem([label]); self.jobs_tree.addTopLevelItem(group); groups[bucket] = group
            item = QTreeWidgetItem([j['customer_name'],*[self._field_value(j,f,'jobs') for f in cols]])
            item.setData(0,Qt.ItemDataRole.UserRole,j['id']); groups[bucket].addChild(item)
        self.jobs_tree.expandAll()
        for col in range(1+len(cols)): self.jobs_tree.resizeColumnToContents(col)

    def refresh_home(self):
        m = self.db.dashboard()
        self.metrics.setText(f"{m['active_customers']} active customers   |   {m['upcoming_jobs']} open jobs   |   {m['overdue_jobs']} overdue jobs\nCompleted this month: ${Decimal(m['completed_month_cents']) / 100:,.2f}")
        rows = []
        for c in self.db.list_customers():
            s = self.db.customer_summary(c['id'])
            if s['next_due']: rows.append({**c,**s})
        rows.sort(key=lambda c:(c['next_due'],c['name'].casefold(),c['id']))
        self.due_table.setRowCount(len(rows))
        for row,c in enumerate(rows):
            for col,value in enumerate([c['name'],c['suburb'],display(c['next_due'],'date'),display(c['next_scheduled'],'date')]):
                item = QTableWidgetItem(value); item.setData(Qt.ItemDataRole.UserRole,c['id']); self.due_table.setItem(row,col,item)

    def refresh_all(self):
        self.refresh_customers(); self.refresh_jobs(); self.refresh_home()

    def apply_settings(self, settings):
        self.settings = settings; self.db.settings = settings; self.refresh_all()

    def add_customer(self):
        dialog = CustomerDialog(self.db,self.settings,parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.selected_customer = dialog.saved_id; self.refresh_all(); self.tabs.setCurrentIndex(1)

    def edit_customer(self):
        if self.selected_customer is None: return self._need_selection('customer')
        if CustomerDialog(self.db,self.settings,self.selected_customer,self).exec() == QDialog.DialogCode.Accepted: self.refresh_all()

    def add_job(self, customer_id=None):
        # Qt's clicked(bool) must not be mistaken for an integer customer ID.
        if isinstance(customer_id,bool): customer_id = None
        if not self.db.list_customers():
            QMessageBox.information(self,'Add a customer first','Create an active customer before adding a job.'); return
        try:
            d = JobDialog(self.db,self.settings,customer_id=customer_id,parent=self)
            if d.exec() == QDialog.DialogCode.Accepted: self.refresh_all()
        except ValueError as exc: QMessageBox.warning(self,'Cannot add job',str(exc))

    def toggle_customer(self):
        if self.selected_customer is None: return self._need_selection('customer')
        c = self.db.get_customer(self.selected_customer)
        action = 'Deactivate' if c['active'] else 'Activate'
        if QMessageBox.question(self,action+' customer?',f"{action} {c['name']}? Their jobs and service history are retained.") != QMessageBox.StandardButton.Yes: return
        self.db.set_customer_active(c['id'],not c['active']); self.refresh_all()

    def open_due_customer(self,row,_col):
        self.selected_customer = self.due_table.item(row,0).data(Qt.ItemDataRole.UserRole)
        self.customer_search.clear(); self.refresh_customers(); self.tabs.setCurrentIndex(1)

    def _selected_job(self):
        item = self.jobs_tree.currentItem()
        return item.data(0,Qt.ItemDataRole.UserRole) if item else None

    def edit_history_job(self,row,_col):
        self._edit_job_id(self.history.item(row,0).data(Qt.ItemDataRole.UserRole))

    def edit_job(self):
        self._edit_job_id(self._selected_job())

    def _edit_job_id(self,job_id):
        if job_id is None: return self._need_selection('job')
        if self.db.get_job(job_id)['deleted_at']:
            QMessageBox.information(self,'Restore job first','Restore this job from Trash before editing it.'); return
        if JobDialog(self.db,self.settings,job_id=job_id,parent=self).exec() == QDialog.DialogCode.Accepted: self.refresh_all()

    def _need_selection(self,entity):
        QMessageBox.information(self,'Select '+entity,'Select a '+entity+' record first.')

    def _job_action(self, action):
        job_id = self._selected_job()
        if job_id is None: return self._need_selection('job')
        try: action(job_id)
        except Exception as exc: QMessageBox.warning(self,'Job could not be updated',str(exc)); return
        self.refresh_all()

    def mark_completed(self): self._job_action(self.db.complete_job)

    def trash_job(self):
        if QMessageBox.question(self,'Move job to Trash?','The job can be restored later. It will be excluded from summaries.') == QMessageBox.StandardButton.Yes:
            self._job_action(self.db.trash_job)

    def restore_job(self): self._job_action(self.db.restore_job)

    @staticmethod
    def _csv_text(value):
        # Text values beginning with formula characters must remain text in spreadsheets.
        return "'"+value if value.lstrip().startswith(('=','+','-','@','\t','\r')) else value

    def _export(self,records,entity,filename):
        path,_ = QFileDialog.getSaveFileName(self,'Export CSV',filename,'CSV files (*.csv)')
        if not path: return
        fields = [f for f in self.settings.fields_for(entity) if f.enabled]
        headings = ['ID'] + (['Customer ID','Customer'] if entity == 'jobs' else []) + [f.label for f in fields]
        try:
            with open(path,'w',newline='',encoding='utf-8-sig') as h:
                writer = csv.writer(h); writer.writerow(headings)
                for r in records:
                    values = [str(r['id'])] + ([str(r['customer_id']),r['customer_name']] if entity == 'jobs' else []) + [self._field_value(r,f,entity) for f in fields]
                    writer.writerow([self._csv_text(v) for v in values])
        except OSError as exc: QMessageBox.warning(self,'Export failed',str(exc)); return
        self.statusBar().showMessage('Exported '+path,10000)

    def export_customers(self): self._export(self.customer_rows,'customers','customers.csv')
    def export_jobs(self): self._export(self.job_rows,'jobs','jobs.csv')

    def automatic_backup(self):
        if not self.backup_manager: return
        try:
            path = self.backup_manager.create_backup_if_due()
            latest = path or self.backup_manager.latest_backup()
            self.backup_label.setText('Latest encrypted backup: '+str(latest))
        except Exception as exc:
            self.backup_label.setText('Automatic backup failed: '+str(exc))

    def manual_backup(self):
        if not self.backup_manager: return
        try:
            path = self.backup_manager.create_backup(); self.backup_manager.prune_backups()
            self.backup_label.setText('Latest encrypted backup: '+str(path))
        except Exception as exc: QMessageBox.warning(self,'Backup failed',str(exc)); return
        QMessageBox.information(self,'Backup created',str(path))

    def show_normal(self):
        self.showNormal(); self.show(); self.raise_(); self.activateWindow()

    def prepare_shutdown(self):
        self.backup_timer.stop()
        self.automatic_backup()
