"""Preserve supplied CSVs; audit consistency and static retrieval, without inventing CAD inputs."""
from pathlib import Path
import hashlib,json,re
import numpy as np
import pandas as pd
from .config import ExperimentConfig
from .metrics import ranking_metrics
from .scoring import fragility_without_indicator,rank_scores
from .synthetic import generate_system

FILES={'catalog':'ehr_components_catalog','edges':'ehr_architecture_edges','matrix':'ehr_dependency_matrix','historical':'ehr_historical_fragility_t1','incidents':'ehr_maintenance_and_incidents_t2'}
INDICATORS=['instability','cycle_participation','defect_density_t1','change_coupling','test_gap_ratio']


def validate_primary_key(frame,column):
    if column not in frame or frame[column].isna().any() or frame[column].duplicated().any():
        raise ValueError(f'missing or duplicate key: {column}')


def _integer_ids(series):
    values=pd.to_numeric(series,errors='raise').to_numpy(dtype=float)
    if not np.isfinite(values).all() or not np.equal(values,np.floor(values)).all():
        raise ValueError('component identifiers must be finite integers')
    return values.astype(int)


def audit_data(data_dir,output_dir):
    data_dir,output_dir=Path(data_dir),Path(output_dir);paths={}
    for key,suffix in FILES.items():
        matches=list(data_dir.glob('*'+suffix+'.csv'))
        if len(matches)!=1:raise ValueError(f'expected exactly one source for {suffix}')
        paths[key]=matches[0]
    frames={key:pd.read_csv(path) for key,path in paths.items()}
    c,h,e,matrix,inc=[frames[key] for key in ('catalog','historical','edges','matrix','incidents')]
    for frame in (c,h):
        validate_primary_key(frame,'component_id');frame['component_id']=_integer_ids(frame.component_id)
    validate_primary_key(inc,'incident_id')
    c=c.sort_values('component_id').set_index('component_id');h=h.sort_values('component_id').set_index('component_id');ids=c.index.to_numpy(dtype=int)
    if len(ids)<10 or not np.array_equal(ids,h.index.to_numpy()):raise ValueError('catalog and historical keys must match; at least ten components required')
    inc['component_id']=_integer_ids(inc.component_id)
    for key in ('source_id','target_id'):e[key]=_integer_ids(e[key])
    if not set(inc.component_id).issubset(set(ids)) or not set(e.source_id).union(e.target_id).issubset(set(ids)):raise ValueError('unknown component reference')
    if e.duplicated(['source_id','target_id']).any():raise ValueError('duplicate directed edges')
    if not np.array_equal(c.service_name.to_numpy(),h.service_name.to_numpy()):raise ValueError('historical component name mismatch')
    if not np.array_equal(inc.service_name.to_numpy(),c.service_name.reindex(inc.component_id).to_numpy()):raise ValueError('incident component name mismatch')
    for key,name in (('source_id','source_name'),('target_id','target_name')):
        if not np.array_equal(e[name].to_numpy(),c.service_name.reindex(e[key]).to_numpy()):raise ValueError('edge component name mismatch')
    labels=[f'C{x:02d}' for x in ids]
    if matrix.iloc[:,0].tolist()!=labels or matrix.columns[1:].tolist()!=labels:raise ValueError('matrix row/column order differs from IDs')
    observed=matrix.iloc[:,1:].to_numpy(dtype=float)
    if observed.shape!=(len(ids),len(ids)) or not np.isin(observed,[0,1]).all():raise ValueError('matrix must be square and binary')
    adjacency=np.zeros_like(observed,dtype=int);positions={x:k for k,x in enumerate(ids)}
    for source,target in zip(e.source_id,e.target_id):adjacency[positions[source],positions[target]]=1
    z=h[INDICATORS].to_numpy(dtype=float)
    if not np.isfinite(z).all() or (z<0).any() or (z>1).any():raise ValueError('historical indicators must be finite normalized values')
    weights=ExperimentConfig().fragility_weights;computed=z@np.asarray(weights);provided=h.fragility_score_t1.to_numpy(dtype=float)
    if not np.isfinite(provided).all():raise ValueError('nonfinite supplied fragility')
    effort=pd.to_numeric(inc.resolution_effort_hours,errors='raise').to_numpy(dtype=float)
    if not np.isfinite(effort).all() or (effort<0).any():raise ValueError('invalid incident effort')
    dates=pd.to_datetime(inc.timestamp,format='ISO8601',errors='raise')
    def window(frame,column):
        values=frame[column].unique()
        if len(values)!=1:raise ValueError('inconsistent window labels')
        bounds=re.findall(r'\d{4}-\d{2}-\d{2}',str(values[0]))
        if len(bounds)!=2:raise ValueError('window label requires two dates')
        return pd.Timestamp(bounds[0]),pd.Timestamp(bounds[1])+pd.Timedelta(days=1)
    t1_start,t1_end=window(h,'observation_window');t2_start,t2_end=window(inc,'evaluation_window')
    if t1_start>=t1_end or t2_start>=t2_end:raise ValueError('invalid window order')
    if not ((dates>=t2_start)&(dates<t2_end)).all():raise ValueError('incident outside declared T2 window')
    relevant=np.isin(ids,inc.component_id.unique());metric_rows=[];rank_rows=[]
    for name,score in [('Supplied T1 static fragility',provided),('Recomputed T1 static fragility',computed),('T1 static fragility without defect density',fragility_without_indicator(z,weights,2))]:
        order=rank_scores(score);metrics=ranking_metrics(order,relevant)
        metric_rows.append(dict(method=name,p_at_10=metrics.p_at_10,r_at_10=metrics.r_at_10,average_precision=metrics.average_precision,reciprocal_rank=metrics.reciprocal_rank))
        rank_rows.extend(dict(method=name,rank=k+1,component_id=int(ids[j]),score=float(score[j]),has_t2_incident=bool(relevant[j])) for k,j in enumerate(order))
    ca=adjacency.sum(axis=0);ce=adjacency.sum(axis=1)
    derived=pd.DataFrame(dict(component_id=ids,reported_Ca=c.afferent_coupling_Ca.to_numpy(),graph_Ca=ca,reported_Ce=c.efferent_coupling_Ce.to_numpy(),graph_Ce=ce,graph_instability=np.divide(ce,ca+ce,out=np.zeros(len(ids),float),where=(ca+ce)>0)))
    original=generate_system(ExperimentConfig());counts=inc.groupby('component_id').size().reindex(range(45),fill_value=0).to_numpy()
    report={'scope':'Read-only consistency audit and single static rankings; no full CAD or process-discovery validation',
        'source_origin':'User identifies five CSVs as real; original extraction and attribution records are not supplied',
        'source_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths.values()},
        'audit_source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'rows':{key:len(frame) for key,frame in frames.items()},
        'checks':{'matrix_matches_edges':bool(np.array_equal(adjacency,observed)),'catalog_Ca_disagreements':int((c.afferent_coupling_Ca.to_numpy()!=ca).sum()),'catalog_Ce_disagreements':int((c.efferent_coupling_Ce.to_numpy()!=ce).sum()),'provided_fragility_max_absolute_error':float(abs(provided-computed).max()),'score_within_four_decimal_rounding_bound':bool(np.allclose(provided,computed,rtol=0,atol=1e-4)),'declared_windows_temporally_separated':bool(t1_end<=t2_start),'t2_incidents_within_declared_window':True,'t2_component_counts_equal_original_synthetic_label_counts':bool(set(ids)==set(range(45)) and np.array_equal(counts,original.defect_counts))},
        't1_window_label':h.observation_window.iloc[0],'t2_window_label':inc.evaluation_window.iloc[0],
        't2_timestamp_range':[str(dates.min()),str(dates.max())],'t2_components_with_incidents':int(relevant.sum()),'t2_total_reported_effort_hours':float(effort.sum()),
        'attribution_field_values':inc.attributed_by.unique().tolist(),'excluded_from_t1_field_values':inc.in_t1_defect_density_indicator.astype(str).unique().tolist(),'retrieval':metric_rows,
        'not_established':['Original extraction/source-record identifiers','Independent attribution and overlap provenance','T1 indicator definitions, normalization bounds and raw historical counts','Dependency scope explaining Ca discrepancies','Case-level event logs and distributed spans','Historical pathway frequencies, criticality and trace-to-component incidence','Individual criticality ratings','Matched established ATD implementation','Prospective maintenance effect','Production scale'],
        'interpretation':'Window labels and attribution strings are file assertions. Incident pathway IDs are outcomes and never used to construct historical exposure. Static retrieval has one ranking per score, without run-level confidence intervals or CAD scores.'}
    output_dir.mkdir(parents=True,exist_ok=True)
    pd.DataFrame(metric_rows).to_csv(output_dir/'static_retrieval.csv',index=False)
    pd.DataFrame(rank_rows).to_csv(output_dir/'static_rankings.csv',index=False)
    derived.to_csv(output_dir/'derived_dependency_checks.csv',index=False)
    (output_dir/'data_audit.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    rows=[f"{row['method']} & {row['p_at_10']:.3f} & {row['r_at_10']:.3f} & {row['average_precision']:.3f} & {row['reciprocal_rank']:.3f} \\\\" for row in metric_rows]
    (output_dir/'data_audit_results.tex').write_text('% Generated from supplied CSV audit; not full CAD evaluation.\n'+r'\newcommand{\CADSuppliedStaticRows}{'+'\n'+'\n'.join(rows)+'\n}\n')
    return report
