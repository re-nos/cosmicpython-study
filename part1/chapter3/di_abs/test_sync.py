import pytest

from sync import sync


class FakeFileSystem(list):
    def copy(self, src, dst):
        self.append(('copy', src, dst))
        
    def move(self, src, dst):
        self.append(('move', src, dst))
        
    def delete(self, dst):
        self.append(('delete', dst))
        

def test_when_a_file_exists_in_the_source_but_not_the_destination():
    source = {'sha1': 'my-file'}
    dest = {}
    filesystem = FakeFileSystem()
    
    reader = {'/source': source, '/dest': dest}
    sync(reader.pop, filesystem, '/source', '/dest')
    
    assert filesystem == ['copy', '/source/my-file', '/dest/my-file']
    
    
def test_when_a_file_has_been_renamed_in_the_source():
    source = {'sha1': 'renamed-file'}
    dest = {'sha1': 'original-file'}
    filesystem = FakeFileSystem()
    
    reader = {'/source': source, '/dest': dest}
    sync(reader.pop, filesystem, '/source', '/dest')
    
    assert filesystem == ['move', '/dest/renamed-file', '/dest/renamed-file']
        