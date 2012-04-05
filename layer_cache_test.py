#!/user/bin/env python

import layer_cache
import request_cache as cachepy
from google.appengine.api import memcache
from google.appengine.ext import db
from testutil import GAEModelTestCase

class LayerCacheTest(GAEModelTestCase):

    def setUp(self):
        # big_string is bigger than the 1MB memcache and datastore limits and
        # so chunks should get used
        self.big_string = "a"*1000000+"b"*1000000
        
        # huge_string is bigger than the 32MB limit for api requests that 
        # memcache.set_multi would hit
        self.huge_string = "a"*34000000

        self.key = "__layer_cache_layer_cache_test.func__"
        super(LayerCacheTest, self).setUp()

class LayerCacheMemcacheTest(LayerCacheTest):

    def setUp(self):
        @layer_cache.cache(layer=layer_cache.Layers.Memcache,
                           compress_chunks=False)
        def func(result):
            return result

        self.cache_func=func
        super(LayerCacheMemcacheTest, self).setUp()

    def test_memcache_should_return_cached_result(self):
        self.cache_func("a")
        self.assertEqual("a", self.cache_func("b"))

    def test_large_memcache_should_chunk_and_return_cached_result(self):
        self.cache_func(self.big_string)
        self.assertIsNotNone(memcache.get(self.key + "__chunk0__"))
        self.assertEqualTruncateError(self.big_string, self.cache_func("a"))

    def test_should_throw_out_result_on_missing_chunk_and_reexecute(self):
        self.cache_func(self.big_string)
        # deleting the 2nd chunk ... next time we get it pickle.loads should 
        # throw an error and the target func will be rexecuted
        memcache.delete(self.key + "__chunk1__")
        self.assertEqualTruncateError("a", self.cache_func("a"))

    def test_should_throw_out_result_when_wrong_chunk_is_read(self):
        ''' Tests to make sure results are recalculated when a chunk is corrupt 
        
        If ChunkedResult in a race condition read from a previous version of a
        key then depickling should fail.  This will test that it failed silently
        and that the results are then recalculated.
        '''

        self.cache_func(self.big_string)
        # overwriting the 1st chunk ... next time we get it pickle.loads should 
        # throw an error and the target func will be rexecuted
        memcache.set(self.key + "__chunk1__", "depickle fail")
        self.assertEqualTruncateError("a", self.cache_func("a"))
    
    def test_huge_memcache_set_should_fail_gracefully_and_reexecute(self):
        self.cache_func(self.huge_string)
        self.assertEqualTruncateError("a", self.cache_func("a"))
    
    def test_use_chunks_parameters_forces_chunking_for_small_size(self):
        @layer_cache.cache(layer=layer_cache.Layers.Memcache, use_chunks=True)
        def func(result):
            return result

        func("a")
        self.assertIsInstance(memcache.get(self.key), layer_cache.ChunkedResult)

    
class LayerCacheDatastoreTest(LayerCacheTest):

    def setUp(self):
        @layer_cache.cache(layer=layer_cache.Layers.Datastore,
                           compress_chunks=False)
        def func(result):
            return result

        self.cache_func = func
        super(LayerCacheDatastoreTest, self).setUp()

    def test_datastore_should_return_cached_result(self):
        self.cache_func("a")
        
        # asserting that we are not using chunks
        self.assertNotIsInstance(layer_cache.KeyValueCache.get(self.key, None),
            layer_cache.ChunkedResult)

        self.assertEqual("a", self.cache_func("b"))
    
    def test_large_datastore_should_chunk_and_return_cached_result(self):        
        self.cache_func(self.big_string)

        # asserting that it is using chunks
        self.assertIsInstance(layer_cache.KeyValueCache.get(self.key, None),
            layer_cache.ChunkedResult)
        
        # asserting that it is returning the cached result
        self.assertEqualTruncateError(self.big_string, self.cache_func("a"))

    def test_chunked_result_deletion_leaves_no_chunks_behind(self):
        self.cache_func(self.big_string)
        layer_cache.ChunkedResult.delete(
            self.key, 
            namespace=None,
            cache_class=layer_cache.KeyValueCache)

        # deleting the 2nd chunk ... next time we get it pickle.loads should 
        # throw an error and the target func will be rexecuted
        values = layer_cache.KeyValueCache.get_multi([
            self.key, 
            self.key + "__chunk1__", 
            self.key + "__chunk2__", 
            self.key + "__chunk3__"], namespace=None)

        # assert that all entries are now gone
        self.assertEqual(0, len(values))

        # assert that we will now recalculate target
        self.assertEqualTruncateError("a", self.cache_func("a"))

  
  
class LayerCacheLayerTest(LayerCacheTest):
        
    def test_missing_inapp_cache_gets_repopulated_when_read_from_memcache(self):
        ''' Tests if missing inapp cache gets repopulated from memcache
        
        It performs the checks on large values that will make use of the 
        ChunkedResult
        '''

        @layer_cache.cache(layer=layer_cache.Layers.Memcache | 
                                 layer_cache.Layers.InAppMemory,
                           compress_chunks=False)
        def func(result):
            return result

        func(self.big_string)
        cachepy.flush()
        
        # make sure cachepy's value is gone
        self.assertIsNone(cachepy.get(self.key))
                
        # make sure we are still able to get the value from memcache
        self.assertEqualTruncateError(self.big_string, func("a"))
        
        # make sure cachepy has been filled again
        self.assertEqualTruncateError(self.big_string, 
            cachepy.get(self.key))

    def test_missing_inapp_and_memcache_get_repopulated_from_datastore(self):
        ''' Tests if result from datastore resaves data to higher levels
         
        It performs the checks on large values that will make use of the 
        ChunkedResult.
        '''

        @layer_cache.cache(layer=layer_cache.Layers.Memcache | 
                                 layer_cache.Layers.Datastore |
                                 layer_cache.Layers.InAppMemory,
                           compress_chunks=False)
        def func(result):
            return result

        func(self.big_string)
        cachepy.flush()
        # make sure cachepy is flushed
        self.assertIsNone(cachepy.get(self.key))
        
        # force removal from memcache
        memcache.delete(self.key)

        # make sure removal worked
        self.assertIsNone(memcache.get(self.key))
        
        # make sure we are still able to get the value from datastore
        self.assertEqualTruncateError(self.big_string, func("a"))
        # make sure cachepy has been filled again
        self.assertEqualTruncateError(self.big_string, 
            cachepy.get(self.key))

        # make sure memcache value has been readded
        self.assertIsInstance(
            memcache.get(self.key),
            layer_cache.ChunkedResult)

class LayerCacheCompressionTest(LayerCacheTest):

    def setUp(self):
        @layer_cache.cache(layer=layer_cache.Layers.Memcache)
        def func(result):
            return result

        self.cache_func = func
        super(LayerCacheCompressionTest, self).setUp()


    def test_with_compression_should_save_in_just_one_chunk(self):
        self.cache_func(self.big_string)
        
        # make sure cache is being used by checking to make sure it is the same
        # length as previous value
        self.assertEqualTruncateError(self.big_string, self.cache_func("a"))

        # check to make sure that only one memcache item got created
        # if compression wasn't working than 4 keys would be set including the
        # following key
        self.assertIsNone(memcache.get(self.key + "__chunk0__"))

    def test_corrupted_uncompressible_chunk_should_reexecute_target(self):
        '''Tests whether decompression fails silently if data is corrupt. 

        It does an assert to see the results are recalculated when a chunk gets 
        somehow corrupted causing decompression to fail.
        '''

        self.cache_func("stuff")
        # overwriting key value ... next time we get it decompress should 
        # throw an error and the target func will be rexecuted
        memcache.set(self.key, 
                     layer_cache.ChunkedResult(data = "decompress fail"))
        self.assertEqual("a", self.cache_func("a"))
    


