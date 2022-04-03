
# x9k3

* __x9k3__ is an __HLS Segmenter with SCTE-35 Support__. 
* __SCTE-35 Cues__ in __MpegTS Streams__ are Translated into HLS tags.
* Segments are __Split on SCTE-35 Cues__ as needed.
* __m3u8__ Manifests are created with __SCTE-35 HLS tags__.
* Supports __h264__ and __h265__(hevc)
* Supports __Files, Http(s), Multicast, and UDP MpegTS__ inputs.  



# Heads Up, 
> This is not yet stable, vis-à-vis bugs.`Expect changes. 
# Be cool.
> Give me a hand.
  * Write Code, if you do that or want to learn.
  * Write Docs, if code is not your thing.
  * Break Stuff_and tell me what happened.
    
 
### Requires 
* python 3.6+ or pypy3
* [threefive](https://github.com/futzu/scte35-threefive)  
```smalltalk
pip3 install threefive
```

### How to Use
```smalltalk
python3 x9k3.py video.mpegts
```
```smalltalk
python3 x9k3.py https://example.com/video.ts
```
```smalltalk
cat video.ts | python3 x9k3.py
```

### Output

* index.m3u8

```smalltalk
#EXTM3U
#EXT-X-VERSION:3
#EXT-X-TARGETDURATION:3
#EXT-X-MEDIA-SEQUENCE:0
 
#EXTINF:2.168833,
seg0.ts
#EXTINF:2.335667,
seg1.ts
#EXTINF:2.168833,
seg2.ts

```

*  SCTE-35 Cues are added when received


```smalltalk
#EXTINF:2.002,
seg5.ts
#EXTINF:2.002,
seg6.ts
#EXTINF:2.002,
seg7.ts
#EXTINF:2.002,
seg8.ts
#EXT-X-SCTE35:CUE="/DBfAAAAAAAAAP/wBQb+W/fXFwBJAg9DVUVJCXDUcX+fASIhAQECD0NVRUkJcNRwf58BIhEBAQIPQ1VFSQlxDxd/nwEEEAEBAhRDVUVJCXEPGH/fAAc0VHABBCABAe6Vhcw=" 
#EXTINF:2.002,
seg9.ts
```

*  Video Segment is cut at splice point.
* SCTE-35 Cues are added or repeated.



```smalltalk
#EXT-X-SCTE35:CUE="/DAxAAAAAAAAAP/wFAUAAABdf+/+zHRtOn4Ae6DOAAAAAAAMAQpDVUVJsZ8xMjEqLYemJQ==" CUE-OUT=YES
#EXTINF:1.668334,
seg13.ts

```

* Segments are cut on iframes.
* Segment size is 2 seconds or more, determined by GOP size. 
* Segments are named seg1.ts seg2.ts etc...

```smalltalk
seg47.ts
#EXTINF:2.12,
seg48.ts
#EXTINF:2.12,
seg49.ts
#EXTINF:2.12,
seg50.ts

```

### Test
```
ffplay index.m3u8
```

### 2020 SCTE-35 Specification Regarding The HLS `#EXT-X-SCTE35` Tag

![image](https://user-images.githubusercontent.com/52701496/160178288-fc75bcfc-b408-43f0-a7ec-83ecdfb10e8b.png)
![image](https://user-images.githubusercontent.com/52701496/160177961-aa7f1706-2f49-4144-a3e3-36efb458037d.png)
![image](https://user-images.githubusercontent.com/52701496/160178082-a978772d-d650-4093-a442-2aeb907bba19.png)






