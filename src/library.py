"""Read-only recording groups and explicit research-corpus boundaries."""
from collections import Counter


def source_category(report, references=()):
    metadata=report.get('metadata',{})
    for ref in references:
        origin=ref.get('origin',{})
        if origin.get('kind')=='published_human_dataset':
            return 'research',origin.get('dataset','published dataset')
    dataset=metadata.get('dataset') or report.get('provenance',{}).get('dataset')
    if dataset:
        return 'research',str(dataset)
    # Backstop for legacy imported Vocadito reports without reference sidecars.
    path=str(report['audio'].get('source_path','')).replace('\\','/').lower()
    if '/vocadito/' in path or str(metadata.get('artist','')).lower().startswith('vocadito '):
        return 'research','vocadito (legacy provenance)'
    if metadata.get('source_category')=='research':
        return 'research','user-declared research'
    return 'personal',None


def recording_groups(rows, references=()):
    by_source={};refs={}
    for reference in references:
        refs.setdefault(reference['audio']['content_sha256'],[]).append(reference)
    for row in rows:
        source=row['audio']['content_sha256'];group=by_source.setdefault(source,[]);group.append(row)
    groups=[]
    for source,versions in by_source.items():
        # Stable preference; browsing another model never silently changes corpus input.
        versions=sorted(versions,key=lambda v:(v['model']['name']!='heuristic',v.get('estimator',''),v['id']))
        preferred=versions[0];metadata=preferred['metadata'];source_refs=refs.get(source,[])
        categories=[source_category(v,source_refs) for v in versions]
        category,dataset=next((c for c in categories if c[0]=='research'),categories[0])
        name=metadata.get('song') or preferred['audio']['source_path'].replace('\\','/').split('/')[-1]
        artist=metadata.get('artist','')
        groups.append({'source_hash':source,'name':name,'artist':artist,'category':category,'dataset':dataset,
            'song_key':[artist,metadata.get('song') or source],
            'duration':preferred['audio']['duration'],'analysis_ids':[v['id'] for v in versions],
            'preferred_analysis':preferred['id'],'working_revision':next((v['correction_revision'] for v in versions if v.get('correction_revision')),None),
            'references':[{k:r[k] for k in ('id','revision','annotator','review','excerpt','origin','split')} for r in source_refs],
            'aliases':sorted({v['metadata'].get('song','') for v in versions if v['metadata'].get('song')})})
    return sorted(groups,key=lambda g:(g['category']!='personal',g['name'].casefold(),g['source_hash']))


def validate_corpus_sources(reports, references=(), allow_research=False, context_reports=()):
    unique={r['audio']['content_sha256']:r for r in reports}
    ref_map={}
    for r in references:ref_map.setdefault(r['audio']['content_sha256'],[]).append(r)
    context={}
    for report in context_reports:
        source=report['audio']['content_sha256']
        category=source_category(report,ref_map.get(source,[]))
        if source not in context or category[0]=='research':context[source]=category
    categories=Counter();research=[]
    for source,report in unique.items():
        category,dataset=source_category(report,ref_map.get(source,[]))
        if context.get(source,('',None))[0]=='research':category,dataset=context[source]
        categories[category]+=1
        if category=='research':research.append({'source_hash':source,'dataset':dataset})
    if research and allow_research is not True:
        raise ValueError('Research recordings (including Vocadito) are excluded from artist corpora. Explicitly enable research-corpus inclusion before using them.')
    return list(unique.values()),{'unique_recordings':len(unique),'categories':dict(categories),
        'research_opt_in':bool(research and allow_research is True),'research_sources':research}
