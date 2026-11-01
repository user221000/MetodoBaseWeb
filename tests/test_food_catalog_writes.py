"""Invalid food edits cannot mutate their own SQLite catalog or related rows."""
import sqlite3

import pytest


@pytest.mark.parametrize('patch',[
    {'proteina':-1},{'carbs':None},{'grasa':float('nan')},{'kcal':float('inf')},
    {'proteina':True},{'meal_idx':[]},{'meal_idx':[99]},{'meal_idx':[True]},
    {'limite':-5},{'limite':float('nan')},{'limite':True},{'nombre':'   '},
    {'categoria':['verdura']},{'equivalencia':123},
])
def test_invalid_edit_never_changes_existing_nutrients_or_related_rows(tmp_path,patch):
    from src.alimentos_sqlite import guardar_alimento
    # Own empty schema; an explicit path avoids all application data directories.
    path=tmp_path/'foods.db'
    schema='''CREATE TABLE alimentos(nombre TEXT PRIMARY KEY,proteina REAL,carbs REAL,grasa REAL,kcal REAL,meal_idx TEXT);
    CREATE TABLE categorias(categoria TEXT,alimento TEXT,orden INTEGER,PRIMARY KEY(categoria,alimento));
    CREATE TABLE limites(alimento TEXT PRIMARY KEY,limite REAL NOT NULL);
    CREATE TABLE equivalencias(alimento TEXT PRIMARY KEY,equivalencia TEXT NOT NULL);'''
    with sqlite3.connect(path) as db:db.executescript(schema)
    valid={'nombre':'own-food','proteina':5,'carbs':6,'grasa':7,'kcal':107,
           'meal_idx':[0,3],'categoria':'custom','limite':100,'equivalencia':'Pesar en gramos'}
    guardar_alimento(valid,path)
    def snapshot():
        with sqlite3.connect(path) as db:
            return [db.execute('SELECT * FROM '+table).fetchall()
                    for table in ('alimentos','categorias','limites','equivalencias')]
    before=snapshot()
    with pytest.raises(ValueError):guardar_alimento({**valid,**patch},path)
    assert snapshot()==before
