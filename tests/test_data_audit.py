from pathlib import Path
import shutil
import pandas as pd
import pytest
from cad_sim.data_audit import audit_data,validate_primary_key

DATA=Path(__file__).resolve().parents[2]/'data'


def test_primary_key_duplicates_and_missing_values_are_rejected():
    for values in ([1,1],[1,None]):
        with pytest.raises(ValueError,match='missing or duplicate key'):
            validate_primary_key(pd.DataFrame({'component_id':values}),'component_id')


@pytest.fixture
def supplied_data(tmp_path):
    if not DATA.is_dir():pytest.skip('Supplementary CSVs are outside the reduced code package')
    target=tmp_path/'data';shutil.copytree(DATA,target)
    return target


def test_supplied_csv_audit_preserves_sources_and_separates_static_results(supplied_data,tmp_path):
    before={p.name:p.read_bytes() for p in supplied_data.glob('*.csv')}
    report=audit_data(supplied_data,tmp_path/'out')
    assert report['checks']['matrix_matches_edges']
    assert report['checks']['catalog_Ca_disagreements']==41
    assert report['checks']['catalog_Ce_disagreements']==0
    assert report['checks']['declared_windows_temporally_separated']
    assert report['retrieval'][0]['p_at_10']==.1
    assert report['retrieval'][0]['r_at_10']==1/12
    assert report['retrieval'][0]['average_precision']==pytest.approx(.22696182125198563)
    assert before=={p.name:p.read_bytes() for p in supplied_data.glob('*.csv')}
    assert len(report['retrieval'])==3
    assert all('CAD' not in x['method'] for x in report['retrieval'])


def test_incident_pathway_and_effort_fields_never_feed_static_predictors(supplied_data,tmp_path):
    first=audit_data(supplied_data,tmp_path/'first')
    path=next(supplied_data.glob('*ehr_maintenance_and_incidents_t2.csv'))
    frame=pd.read_csv(path);frame['affected_pathway_id']=999;frame['resolution_effort_hours']=0
    frame.to_csv(path,index=False)
    second=audit_data(supplied_data,tmp_path/'second')
    assert first['retrieval']==second['retrieval']
    assert (tmp_path/'first/static_rankings.csv').read_bytes()==(tmp_path/'second/static_rankings.csv').read_bytes()


@pytest.mark.parametrize('column,value,message',[('component_id',999,'unknown component'),('timestamp','2025-06-01','outside declared T2')])
def test_invalid_incident_keys_or_dates_do_not_produce_results(supplied_data,tmp_path,column,value,message):
    path=next(supplied_data.glob('*ehr_maintenance_and_incidents_t2.csv'))
    frame=pd.read_csv(path);frame.loc[0,column]=value;frame.to_csv(path,index=False)
    with pytest.raises(ValueError,match=message):audit_data(supplied_data,tmp_path/'out')
    assert not (tmp_path/'out').exists()
