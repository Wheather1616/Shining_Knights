"""Functional V1 desktop shell for customers, jobs and field configuration."""
from __future__ import annotations

import csv
from datetime import date
from decimal import Decimal

from PySide6.QtCore import Qt, QTimer, QSignalBlocker
from PySide6.QtWidgets import (QDialog, QFileDialog, QHBoxLayout,
    QHeaderView, QLabel, QMainWindow, QMessageBox, QPushButton,
    QTableWidgetItem, QTabWidget,
    QVBoxLayout, QWidget, QAbstractItemView)

from ..backup import DatabaseBackupManager
from ..config import CORE_FIELDS, JOB_FIELDS, JOB_STATUSES, SettingsStore
from ..database import CustomerDatabase
from ..paths import default_backup_dir
from .customer_page import CustomerPage
from .field_settings import FieldSettingsPage
from .forms import CustomerDialog, JobDialog
from .jobs_page import JobsPage
from .home_page import HomePage


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
        from ..recovery import recover_interrupted_restore
        recover_interrupted_restore(db.db_path if db else self.settings.db_path, self.store)
        self.settings = self.store.load()
        self.db = db or CustomerDatabase(self.settings.db_path,self.settings)
        self.db.settings = self.settings
        self.selected_customer = None
        self.backup_manager = DatabaseBackupManager(self.db.db_path,default_backup_dir(),self.db.key_hex,settings_store=self.store) if enable_backups else None
        self.setWindowTitle('ShiningKnights | Customers & Jobs')
        self.resize(1250,820)
        self.setMinimumSize(900, 690)
        self.tabs = QTabWidget()
        self.tabs.setObjectName('AppTabs')
        self._build_shell()
        self._home_page()
        self._customer_page()
        self._jobs_page()
        self.configuration = FieldSettingsPage(self.settings,self.store,owner=self)
        self.configuration.settings_saved.connect(self.apply_settings)
        self.configuration.customers_requested.connect(lambda: self.tabs.setCurrentIndex(1))
        self.tabs.addTab(self.configuration,'Settings')
        self._active_tab = self.tabs.currentIndex()
        self._changing_tab = False
        self.tabs.currentChanged.connect(self._tab_changed)
        self.jobs_page.load_preferences()

        self.refresh_all()
        self.backup_timer = QTimer(self)
        self.backup_timer.timeout.connect(self.automatic_backup)
        if self.backup_manager:
            self.backup_timer.start(60 * 60 * 1000)
            self.automatic_backup()
        self.overview_timer = QTimer(self)
        self.overview_timer.timeout.connect(self._check_overview_date)
        self.overview_timer.start(60 * 1000)

    def _button(self, label, handler):
        b = QPushButton(label)
        role = 'primary' if label.startswith('Add ') or label == 'Mark completed' else 'accent' if label in ('Export CSV','Restore job') else 'danger' if label == 'Move to Trash' else 'secondary'
        b.setProperty('role',role)
        b.clicked.connect(handler)
        return b

    def _build_shell(self):
        shell = QWidget()
        shell.setObjectName('AppShell')
        layout = QVBoxLayout(shell)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.app_header = QWidget()
        self.app_header.setObjectName('AppHeader')
        header = QHBoxLayout(self.app_header)
        header.setContentsMargins(24, 14, 24, 14)
        header.setSpacing(12)
        brand = QLabel('Shining Knights')
        brand.setObjectName('AppBrand')
        header.addWidget(brand)
        header.addSpacing(20)
        self.navigation_buttons = []
        for index, (caption, shortcut) in enumerate((('Home', 'Alt+H'), ('Customers', 'Alt+C'), ('Jobs', 'Alt+J'), ('Settings', 'Alt+S'))):
            button = QPushButton(caption)
            button.setObjectName('AppNavigation')
            button.setCheckable(True)
            button.setShortcut(shortcut)
            button.setAccessibleName(caption + ' page')
            button.clicked.connect(lambda _=False, i=index: self._navigate(i))
            header.addWidget(button)
            self.navigation_buttons.append(button)
        header.addStretch()
        layout.addWidget(self.app_header)
        self.tabs.tabBar().hide()
        layout.addWidget(self.tabs, 1)
        self.setCentralWidget(shell)

    def _navigate(self, index):
        self.tabs.setCurrentIndex(index)
        self._sync_navigation()

    def _sync_navigation(self):
        for index, button in enumerate(self.navigation_buttons):
            button.setChecked(index == self.tabs.currentIndex())

    def _home_page(self):
        self.home = HomePage(self)
        self.backup_label = self.home.backup_label
        self.tabs.addTab(self.home, 'Home')
        self._sync_navigation()

    def open_home_jobs(self, kind='all', job_id=None):
        page = self.jobs_page
        # A Home link is an explicit filter change; stored filters must not hide its target.
        widgets = (page.search, page.status_filter, page.date_range, page.group_by)
        blockers = [QSignalBlocker(widget) for widget in widgets]
        page.search.clear()
        page.status_filter.setCurrentText('Overdue' if kind == 'overdue' else 'Upcoming' if kind in ('today', 'next7') else 'All')
        page.date_range.setCurrentIndex(page.date_range.findData(kind if kind in ('today', 'next7') else 'all'))
        page.group_by.setCurrentIndex(page.group_by.findData('date'))
        page.custom_dates.hide()
        del blockers
        page.clear_export_selection()
        self.refresh_jobs()
        if job_id in page.items:
            item = page.items[job_id]
            item.parent().setExpanded(True)
            page.tree.setCurrentItem(item)
            page.tree.scrollToItem(item)
        self.remember_job_filters()
        self.tabs.setCurrentIndex(2)

    def open_home_customer(self, customer_id):
        self.customer_search.clear()
        self.inactive.setChecked(False)
        self.selected_customer = customer_id
        self.refresh_customers()
        self.tabs.setCurrentIndex(1)

    def open_backup_settings(self):
        self.configuration.navigation.setCurrentRow(4)
        self.tabs.setCurrentIndex(3)

    def _check_overview_date(self):
        if self.home.overview['as_of'] != date.today().isoformat():
            self.refresh_home()
            self.refresh_jobs()

    @staticmethod
    def _setup_table(table):
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setStretchLastSection(True)
        table.verticalHeader().setVisible(False)
        table.setAlternatingRowColors(True)
        table.setWordWrap(False)
        table.verticalHeader().setDefaultSectionSize(40)
        table.verticalHeader().setMinimumSectionSize(36)

    def _customer_page(self):
        self.customer_page = CustomerPage(self)
        self.customer_table = self.customer_page.customer_table
        self.customer_search = self.customer_page.search
        self.inactive = self.customer_page.inactive
        self.profile = self.customer_page.profile
        self.history = self.customer_page.history
        self.tabs.addTab(self.customer_page, 'Customers')

    def _jobs_page(self):
        self.jobs_page = JobsPage(self)
        self.job_search = self.jobs_page.search
        self.job_filter = self.jobs_page.status_filter
        self.group_by = self.jobs_page.group_by
        self.jobs_tree = self.jobs_page.tree
        self.tabs.addTab(self.jobs_page, 'Jobs')

    def _columns(self, entity):
        from .field_settings import PROTECTED_COLUMNS
        return [f for f in self.settings.fields_for(entity) if f.enabled and (f.browse_column or f.key in PROTECTED_COLUMNS[entity])]

    def _field_value(self, record, f, entity):
        value = record.get(f.key) if f.key in CORE_FIELDS[entity] else record.get('custom_fields',{}).get(f.key)
        if f.key in ('default_job_type', 'job_type'):
            from ..models import work_description
            return work_description(value or [], record.get(f.key + '_sides', {}))
        return display(value,f.field_type)

    def _fill_table(self, table, records, entity, extra=None):
        cols = self._columns(entity)
        headers = [f.label for f in cols]
        if table is self.history:
            default_labels = {field.key: field.label for field in JOB_FIELDS}
            concise = {'scheduled_date': 'Scheduled', 'completed_date': 'Completed',
                       'status': 'Status', 'job_type': 'Nature of job', 'service_name': 'Service', 'fee': 'Fee (AUD)',
                       'payment_type': 'Payment method', 'payment_status': 'Payment status'}
            headers = [concise.get(field.key, field.label) if field.label == default_labels.get(field.key)
                       else field.label for field in cols]
        if extra: headers = [*headers,*extra.keys()]
        if not headers: headers = ['ID']
        table.setColumnCount(len(headers)); table.setHorizontalHeaderLabels(headers); table.setRowCount(len(records))
        for row,record in enumerate(records):
            values = [self._field_value(record,f,entity) for f in cols]
            if extra: values += [fn(record) for fn in extra.values()]
            if not values: values = [str(record['id'])]
            for col,value in enumerate(values):
                item = QTableWidgetItem(str(value)); item.setData(Qt.ItemDataRole.UserRole,record['id'])
                item.setToolTip(str(value))
                if col < len(cols) and cols[col].field_type == 'currency':
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                table.setItem(row,col,item)

    def refresh_customers(self):
        self.customer_rows = self.db.list_customers(self.customer_search.text(), include_inactive=self.inactive.isChecked())
        summaries = {customer['id']: self.db.customer_summary(customer['id']) for customer in self.customer_rows}
        self.customer_page.set_customers(self.customer_rows, summaries, self.selected_customer)
        self.show_selected_customer()

    @staticmethod
    def frequency_text(customer):
        value, unit = customer['frequency_value'], customer['frequency_unit']
        if not value: return 'One-off / as needed'
        if value == 1: return 'Every ' + unit.rstrip('s')
        return f'Every {value} {unit}'

    def show_selected_customer(self):
        items = self.customer_table.selectedItems()
        self.selected_customer = items[0].data(Qt.ItemDataRole.UserRole) if items else None
        if self.selected_customer is None:
            self.customer_page.clear_customer()
            return
        customer = self.db.get_customer(self.selected_customer)
        self.customer_page.show_customer(customer, self.db.customer_summary(customer['id']), self.db.list_jobs(customer['id']))

    def _filtered_jobs(self):
        label = self.job_filter.currentText()
        grouping = self.group_by.currentData()
        jobs = self.db.list_jobs(status=label if label in JOB_STATUSES else '',include_deleted=label == 'Trash',group_by='date' if grouping == 'completed' else grouping,search=self.job_search.text())
        if label == 'Trash': jobs = [j for j in jobs if j['deleted_at']]
        if label in ('Upcoming','Overdue'): jobs = [j for j in jobs if j['status'] in ('Scheduled','In progress')]
        if label == 'Overdue': jobs = [j for j in jobs if j['scheduled_date'] and j['scheduled_date'] < date.today().isoformat()]
        return self.jobs_page.filter_dates(jobs)

    def refresh_jobs(self):
        self.job_rows = self._filtered_jobs()
        self.jobs_page.set_jobs(self.job_rows)

    def refresh_home(self):
        self.home.set_overview(self.db.home_overview(date.today()))

    def refresh_all(self):
        self.refresh_customers(); self.refresh_jobs(); self.refresh_home()

    def apply_settings(self, settings):
        reload_preferences = (self.settings.remember_jobs_filters != settings.remember_jobs_filters or
                              self.settings.jobs_default_group != settings.jobs_default_group)
        self.settings = settings
        self.db.settings = settings
        if reload_preferences:
            self.jobs_page.load_preferences()
        self.refresh_all()

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

    def export_selected_jobs(self):
        records = self.jobs_page.selected_records()
        if records:
            self._export(records, 'jobs', 'selected-jobs.csv')

    def automatic_backup(self):
        if not self.backup_manager: return
        try:
            path = self.backup_manager.create_backup_if_due()
            latest = path or self.backup_manager.latest_backup()
            from datetime import datetime
            self.backup_label.setText('Latest backup: ' + (datetime.fromtimestamp(latest.stat().st_mtime).strftime('%d %B %Y, %I:%M %p') if latest else 'No backup yet'))
            self.configuration.refresh_backup_status()
        except Exception as exc:
            self.backup_label.setText('Automatic backup failed. Check Backups & help in Settings.')
            self.configuration.refresh_backup_status('Automatic backup failed. Please try Back up now.')

    def manual_backup(self):
        if not self.backup_manager: return
        try:
            self.backup_manager.create_backup()
            self.backup_manager.prune_backups()
        except Exception:
            self.configuration.refresh_backup_status('Backup failed. Your records have been kept. Please try again.')
            QMessageBox.warning(self,'Backup failed','A backup could not be created. Your current records have been kept. Please try again.')
            return
        self.configuration.refresh_backup_status()
        self.backup_label.setText(self.configuration.backup_status.text())
        self.statusBar().showMessage('Backup created',10000)

    def restore_database_backup(self):
        if not self.backup_manager: return
        from ..recovery import inspect_backup, restore_backup
        from .restore_dialog import RestoreDialog
        path,_ = QFileDialog.getOpenFileName(self,'Choose a backup',str(self.backup_manager.backup_dir),'Customer backups (*.db)')
        if not path: return
        try:
            info = inspect_backup(path,self.db.key_hex,self.db.db_path)
        except Exception:
            QMessageBox.warning(self,'Backup could not be opened','Choose a valid customer backup from this app on this computer. Your current records have been kept.')
            return
        dialog = RestoreDialog(info,self)
        if dialog.exec() != QDialog.DialogCode.Accepted: return
        self.backup_timer.stop()
        try:
            settings, safety, _ = restore_backup(self.backup_manager,path,self.store,self.settings,expected_info=info)
        except Exception:
            QMessageBox.warning(self,'Restore could not be completed','The restore could not be completed. Your previous records and a safety copy have been kept where available. Please try again or ask for help.')
        else:
            self.selected_customer = None
            self.customer_search.clear()
            self.job_search.clear()
            self.configuration.reset_settings(settings)
            self.apply_settings(settings)
            self.jobs_page.load_preferences()
            self.refresh_all()
            self.configuration.refresh_backup_status('Backup restored. A safety copy of your previous records has been kept.')
            self.statusBar().showMessage('Backup restored',10000)
        finally:
            self.backup_timer.start(60 * 60 * 1000)

    def _tab_changed(self, index):
        if self._changing_tab: return
        if self._active_tab == 3 and index != 3:
            self._changing_tab = True
            # Keep the draft visible while the decision is made.
            self.tabs.setCurrentIndex(3)
            allowed = self.configuration.confirm_leave()
            self.tabs.setCurrentIndex(index if allowed else 3)
            self._changing_tab = False
            self._active_tab = index if allowed else 3
        else:
            self._active_tab = index
        self._sync_navigation()
        if self.tabs.currentIndex() == 0:
            self._check_overview_date()

    def remember_job_filters(self):
        if not hasattr(self,'configuration') or not self.settings.remember_jobs_filters: return
        filters = self.jobs_page.preference_filters()
        if filters == self.settings.jobs_filters: return
        import copy
        candidate = copy.deepcopy(self.settings)
        candidate.jobs_filters = filters
        try:
            self.store.save(candidate)
        except Exception:
            self.statusBar().showMessage('Job filters could not be remembered. Please try again.',10000)
            return
        self.settings = candidate
        self.db.settings = candidate
        self.configuration.sync_runtime_filters(filters)

    def closeEvent(self, event):
        if self.configuration.confirm_leave():
            event.accept()
        else:
            event.ignore()

    def show_normal(self):
        self.showNormal(); self.show(); self.raise_(); self.activateWindow()

    def prepare_shutdown(self):
        self.backup_timer.stop()
        self.overview_timer.stop()
        self.automatic_backup()
