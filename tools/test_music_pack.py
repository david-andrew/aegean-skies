"""Conversion regressions: tempo, reused MIDI channels, percussion and reproducibility."""
import tempfile, unittest, struct, zlib, os
from pathlib import Path
import mido
from music_pack import read_midi, pack, gm, STRINGS, HARP, TIMPANI, DRUMS, PIANO, opening

class MusicPackTests(unittest.TestCase):
 def test_tempo_changes_and_per_track_channels(self):
  m=mido.MidiFile(ticks_per_beat=480)
  a=mido.MidiTrack(); b=mido.MidiTrack();m.tracks=[a,b]
  a.extend([mido.MetaMessage('set_tempo',tempo=500000),mido.Message('program_change',program=46),mido.Message('note_on',note=60,velocity=100),mido.MetaMessage('set_tempo',tempo=1000000,time=480),mido.Message('note_off',note=60,time=480)])
  b.extend([mido.Message('program_change',program=40),mido.Message('note_on',note=67,velocity=80),mido.Message('note_off',note=67,time=960)])
  # Respect machine scratch policy: caller sets TMPDIR to task scratch.
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'test.mid';m.save(p);notes=read_midi(p)
  self.assertEqual([n[3] for n in notes],[HARP,STRINGS])
  self.assertEqual([n[1] for n in notes],[1.5,1.5])
  one,frames,events=pack(notes);two,*_=pack(notes)
  self.assertEqual(one,two);raw=zlib.decompress(one,-15)
  self.assertEqual(raw[:4],b'MUS1');self.assertEqual(len(raw),16+2*12)
  self.assertEqual(struct.unpack_from('<III',raw,4),(2,56000,56000))
 def test_program_families_and_opening_transposition(self):
  self.assertEqual(gm(47),TIMPANI);self.assertEqual(gm(0,True),DRUMS)
  self.assertEqual(gm(0),PIANO)
  ns=opening();self.assertEqual([n[2] for n in ns[:4]],[61]*4)
  self.assertEqual(max(n[2] for n in ns),73)
  self.assertAlmostEqual(ns[3][0],60/88)

if __name__=='__main__':unittest.main()
