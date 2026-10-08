"""Render the real Settings widgets with disposable synthetic data."""
from pathlib import Path
from tempfile import TemporaryDirectory
from PySide6.QtWidgets import QApplication
from customer_app.config import AppSettings, SettingsStore
from customer_app.database import CustomerDatabase
from customer_app.models import CustomerRecord
from customer_app.ui.main_window import CustomerMainWindow
from customer_app.ui.theme import apply_application_theme

app=QApplication([]);apply_application_theme(app)
output=Path(__file__).parent/'screenshots';output.mkdir(exist_ok=True)
with TemporaryDirectory(prefix='settings-preview-') as temporary:
    root=Path(temporary);settings=AppSettings(db_path=root/'customers.db')
    settings.job_type_options=['Window cleaning','Gutter cleaning','Solar panel cleaning']
    settings.equipment_options=['Water-fed pole','Ladder','Squeegee']
    store=SettingsStore(root/'settings.json');store.save(settings)
    db=CustomerDatabase(settings.db_path,settings,key_hex='12'*32)
    db.create_customer(CustomerRecord(name='Sample customer'))
    window=CustomerMainWindow(db=db,settings_store=store,enable_backups=False)
    window.tabs.setCurrentIndex(3);window.show()
    for size in [(1250,820),(900,690)]:
        window.resize(*size)
        for index,name in enumerate(['services','payments','layout','questions','backups']):
            window.configuration.navigation.setCurrentRow(index)
            for _ in range(4):app.processEvents()
            window.grab().save(str(output/f'settings-{name}-{size[0]}.png'))
    window.configuration.discard();window.close()
