import tempfile,unittest
from pathlib import Path
from src.musical_context import MusicalContext,validate_grid,beat,rhythm,section_projection,section_range_summary
class ContextTests(unittest.TestCase):
 def test_layers_legacy_precision_and_explicit_overlap(self):
  with tempfile.TemporaryDirectory(dir='.cache/tests') as d:
   c=MusicalContext(Path(d));source='a'*64
   legacy={'id':'v','name':'My preserved custom title','type':'verse','start':0.,'end':4.}
   adjacent={'id':'c','name':'Chorus 1','type':'chorus','start':4.-1e-8,'end':8.}
   first=c.save(source,'sections',[legacy,adjacent],None,10)
   self.assertEqual(first['value'][0],legacy)
   analysis=dict(legacy,id='a',start=2,end=6,layer='analysis',overlap_policy='allow')
   saved=c.save(source,'sections',[legacy,adjacent,analysis],first['revision'],10)
   self.assertEqual(len(section_projection(saved['value'])),2)
   self.assertEqual(len(section_projection(saved['value'],'all')),3)
   with self.assertRaisesRegex(ValueError,'explicit'):c.save(source,'sections',[dict(analysis,overlap_policy='reject')],saved['revision'],10)
   with self.assertRaisesRegex(ValueError,'overlap'):c.save(source,'sections',[legacy,dict(adjacent,start=3.5)],saved['revision'],10)
   self.assertEqual(c.get(source,'sections'),saved)
 def test_overlap_summary_and_type_projection_do_not_duplicate_support(self):
  ns=[{'id':'n','pitch':60},{'id':'m','pitch':64}]
  row={'work_id':'work','source_hash':'source','notes':ns,'section':{'id':'a','start':0,'end':4}}
  duplicate={**row,'section':{'id':'b','start':1,'end':3}}
  self.assertEqual(section_range_summary([row,duplicate]),section_range_summary([row]))
 def test_revision_validation_and_source_separation(self):
  with tempfile.TemporaryDirectory() as d:
   c=MusicalContext(Path(d));h='a'*64
   s=[{'id':'a','name':'Chorus 1','type':'chorus','start':1.,'end':3.}]
   first=c.save(h,'sections',s,None,10)
   self.assertEqual(c.get(h,'sections'),first)
   with self.assertRaisesRegex(ValueError,'changed'):c.save(h,'sections',s,None,10)
   with self.assertRaisesRegex(ValueError,'overlap'):c.save(h,'sections',s+[dict(s[0],id='b',start=2)],first['revision'],10)
   self.assertIsNone(c.get('b'*64,'sections')['revision'])
   c.save(h,'grid',{'tempo':120,'origin':.5,'confirmed':False},None,10)
   self.assertEqual(c.get(h,'sections'),first)
 def test_grid_and_rhythm(self):
  g=validate_grid({'tempo':120,'origin':.5,'confirmed':True})
  self.assertAlmostEqual(beat(.4,g),-.2)
  row=rhythm([{'id':'n','start':1.,'end':2.6,'pitch':60,'confidence':.8}],g,0,4)
  self.assertEqual(row['status'],'confirmed_grid_observations')
  self.assertEqual(row['events'][0]['onset_beats'],1)
  self.assertTrue(row['events'][0]['crosses_bar'])
  g['confirmed']=False;self.assertEqual(rhythm([],g,0,4)['status'],'provisional_preview')
  self.assertEqual(rhythm([],None,0,4)['status'],'unavailable')
 def test_bad_grid(self):
  for g in [{'tempo':float('nan')},{'meter':[4,3]},{'unit':0}]:
   with self.assertRaises(ValueError):validate_grid(g)

 def test_confirmed_coverage_is_not_global(self):
  g=validate_grid({'tempo':120,'confirmed':True,'validity':[1,3]})
  self.assertEqual(rhythm([],g,0,4)['status'],'provisional_preview')
  self.assertEqual(rhythm([],g,1,3)['status'],'confirmed_grid_observations')
 def test_meter_idea_and_chord_limits(self):
  from src.learning import idea_config,idea_notes,chord_spans
  c=idea_config({'bars':2,'time_signature':[3,4]})
  self.assertEqual(c['time_signature'],[3,4])
  row={'id':'n','start':5,'end':6.1,'pitch':60,'confidence':1}
  with self.assertRaises(ValueError):idea_notes([row],c)
  self.assertEqual(chord_spans('C | G',0,60,[3,4])[-1]['end'],6)
