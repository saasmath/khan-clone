#!/user/bin/env python

import testutil
import layer_cache
import request_cache as cachepy
from google.appengine.api import memcache

class LayerCacheTest(testutil.GAEModelTestCase):
    """
    def test_memcache(self):

        @layer_cache.cache(layer=layer_cache.Layers.Memcache)
        def func1(result):
            return result

        func1("a")
        self.assertEqual("a", func1("b"))
       
    def test_large_memcache(self):
        ''' This test will test something that will make use of multiple chunks
        '''
        @layer_cache.cache(layer=layer_cache.Layers.Memcache,
                           compress_chunks=False)
        def func2(result):
            return result

        func2("a"*1000000+"b"*1000000)
        self.assertEqual(2000000, len(func2("a")))
    

    def test_missing_chunk(self):
        ''' This will test that results are recalculated when chunk is missing
        '''

        @layer_cache.cache(layer=layer_cache.Layers.Memcache, 
                           compress_chunks=False)
        def func3(result):
            return result

        func3("a"*1000000+"b"*1000000)
        # deleting the 2nd chunk ... next time we get it pickle.loads should 
        # throw an error and the target func will be rexecuted
        memcache.delete("__layer_cache_layer_cache_test.func3__2")
        self.assertEqual(1, len(func3("a")))

    def test_corrupted_chunk(self):
        ''' This will test that results are recalculated when a chunk gets 
        somehow corrupted so depickle will fail
        '''
        @layer_cache.cache(layer=layer_cache.Layers.Memcache, 
                           compress_chunks=False)
        def func4(result):
            return result

        func4("a"*1000000+"b"*1000000)
        # deleting the 2nd chunk ... next time we get it pickle.loads should 
        # throw an error and the target func will be rexecuted
        memcache.set("__layer_cache_layer_cache_test.func4__1", "depickle fail")
        self.assertEqual(1, len(func4("a")))
    """
    """ Commenting out as it takes too long
    def test_huge_memcache(self):
        ''' This will test setting a value > 32 MB '''

        @layer_cache.cache(layer=layer_cache.Layers.Memcache,
                           compress_chunks=False)
        def func5(result):
            return result

        func5("a"*33000000)
        self.assertEqual(33000000, len(func5("a")))
    """
    """
    def test_datastore(self):
        ''' Basic sanity check to make sure datastore can be written and read 
        from
        '''
        @layer_cache.cache(layer=layer_cache.Layers.Datastore,
                           compress_chunks=False)
        def func6(result):
            return result

        func6("a")
        self.assertEqual("a", func6("b"))
    
    def test_large_datastore(self):
        ''' Test that the datastore works with Chunked Results '''
        
        @layer_cache.cache(layer=layer_cache.Layers.Datastore,
                           compress_chunks=False)
        def func7(result):
            return result

        func7("a"*1000000+"b"*1000000)
        self.assertEqual(2000000, len(func7("a")))
    """
    """ Commenting out as it takes too long
    def test_huge_datastore(self):
        ''' This will test setting a value > 32 MB in the datastore '''

        @layer_cache.cache(layer=layer_cache.Layers.Datastore,
                           compress_chunks=False)
        def func8(result):
            return result

        func8("a"*33000000)
        self.assertEqual(33000000, len(func8("a")))
    """
    """
    def test_bubble_up_memcache_save(self):
        ''' This will make sure that if something is missing from inAppMemory
        in layercache that it will correctly save it with the values from
        memcache '''

        @layer_cache.cache(layer=layer_cache.Layers.Memcache | 
                                 layer_cache.Layers.InAppMemory,
                           compress_chunks=False)
        def func9(result):
            return result

        func9("a"*1000000+"b"*1000000)
        cachepy.flush()
        
        # make sure cachepy's value is gone
        self.assertEqual(type(None), 
                type(cachepy.get("__layer_cache_layer_cache_test.func9__")))
                
        # make sure we are still able to get the value from datastore
        self.assertEqual(2000000, len(func9("a")))
        
        # make sure cachepy has been filled again
        self.assertEqual(2000000, 
                    len(cachepy.get("__layer_cache_layer_cache_test.func9__")))

    def test_bubble_up_datastore_save(self):
        ''' This will make sure that if something is missing from a higher level
        in layercache that it will correctly save it with the values from
        the lower levels '''

        @layer_cache.cache(layer=layer_cache.Layers.Memcache | 
                                 layer_cache.Layers.Datastore |
                                 layer_cache.Layers.InAppMemory,
                           compress_chunks=False)
        def func10(result):
            return result

        func10("a"*1000000+"b"*1000000)
        cachepy.flush()
        # make sure cachepy is flushed
        self.assertEqual(type(None), 
            type(cachepy.get("__layer_cache_layer_cache_test.func10__")))
        
        # force removal from memcache
        memcache.delete("__layer_cache_layer_cache_test.func10__")

        # make sure removal worked
        self.assertEqual(type(None),
            type(memcache.get("__layer_cache_layer_cache_test.func10__")))
        
        # make sure we are still able to get the value from datastore
        self.assertEqual(2000000, len(func10("a")))
        # make sure cachepy has been filled again
        self.assertEqual(2000000, 
            len(cachepy.get("__layer_cache_layer_cache_test.func10__")))

        # make sure memcache value has been readded
        self.assertTrue(
            isinstance(memcache.get("__layer_cache_layer_cache_test.func10__"),
                       layer_cache.ChunkedResult))
    
    def test_compress_large_memcache(self):
        ''' This test will test that compressing is working
        '''
        @layer_cache.cache(layer=layer_cache.Layers.Memcache)
        def func11(result):
            return result

        func11("a"*1000000+"b"*1000000)
        
        # make sure cache is being used by checking to make sure it is the same
        # length as previous value
        self.assertEqual(2000000, len(func11("a")))

        # check to make sure that only one memcache item got created
        # if compression wasn't working than 4 keys would be set including the
        # following key
        self.assertEqual(type(None), 
            type(memcache.get("__layer_cache_layer_cache_test.func11__1")))

    def test_use_chunks(self):
        '''This test makes sure that using the use_chunks parameter that it will
        force it to use ChunkResults regardless of size
        '''
        @layer_cache.cache(layer=layer_cache.Layers.Memcache, use_chunks=True)
        def func12(result):
            return result

        func12("a")
        self.assertTrue(isinstance( 
            memcache.get("__layer_cache_layer_cache_test.func12__"),
            layer_cache.ChunkedResult))

    def test_corrupted_uncompressible_chunk(self):
        ''' This will test that results are recalculated when a chunk gets 
        somehow corrupted so decompression will fail
        '''
        @layer_cache.cache(layer=layer_cache.Layers.Memcache)
        def func13(result):
            return result

        func13("stuff")
        # deleting the 2nd chunk ... next time we get it pickle.loads should 
        # throw an error and the target func will be rexecuted
        memcache.set("__layer_cache_layer_cache_test.func13__", 
                     layer_cache.ChunkedResult(data = "decompress fail"))
        self.assertEqual(1, len(func13("a")))
    """
    def test_delete_datastore_chunks(self):
        ''' This will test that all chunks are deleted
        '''
        @layer_cache.cache(layer=layer_cache.Layers.Datastore, 
                           compress_chunks=False)
        def func14(result):
            return result

        func14("a"*1000000+"b"*1000000)
        layer_cache.ChunkedResult.delete(
            "__layer_cache_layer_cache_test.func14__", 
            namespace=None,
            cache_class=layer_cache.KeyValueCache)

        # deleting the 2nd chunk ... next time we get it pickle.loads should 
        # throw an error and the target func will be rexecuted
        values = layer_cache.KeyValueCache.get_multi([
            "__layer_cache_layer_cache_test.func14__", 
            "__layer_cache_layer_cache_test.func14__1", 
            "__layer_cache_layer_cache_test.func14__2", 
            "__layer_cache_layer_cache_test.func14__3"], namespace=None)

        # assert that all entries are now gone
        self.assertEqual(0, len(values))

        # assert that we will now recalculate target
        self.assertEqual(1, len(func14("a")))


