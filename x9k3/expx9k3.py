import datetime
import io
import sys
from collections import deque
from operator import itemgetter
from chunk import Chunk
from new_reader import reader
from iframes import IFramer
from scte35 import SCTE35

# from timer import Timer
from window import SlidingWindow
from threefive import Cue
import threefive.stream as strm

MAJOR = "0"
MINOR = "1"
MAINTAINENCE = "76"


def version():
    """
    version prints x9k3's version as a string

    Odd number versions are releases.
    Even number versions are testing builds between releases.

    Used to set version in setup.py
    and as an easy way to check which
    version you have installed.

    """
    return f"{MAJOR}.{MINOR}.{MAINTAINENCE}"


class ExpX9K3(strm.Stream):
    def __init__(self, tsdata, show_null=False):
        super().__init__(tsdata, show_null)
        self.video = tsdata
        self.active_segment = io.BytesIO()
        self.iframer = IFramer(shush=True)
        self.window = SlidingWindow(500)
        self.scte35 = SCTE35()
        self.packet_size = 188
        self.seconds = 2
        self.segnum = 0
        self.started = None
        self.next_start = None
        self.m3u8 = "index.m3u8"
        self.live = False
        self.media_seq = 0
        self.program_date_time_flag = False
        self.discontinuity_sequence = 0
        self.sidecar_file = "sidecar.txt"
        self.sidecar = deque()
        self.output_dir = "."
        self.shulga = False
        self.delete = False

    def _header(self):
        bump = ""
        self.media_seq = self.window.panes[0].num
        head = [
            "#EXTM3U",
            "#EXT-X-VERSION:3",
            f"#EXT-X-TARGETDURATION:{int(self.seconds+1)}",
            f"#EXT-X-MEDIA-SEQUENCE:{self.media_seq}",
        ]
        if not self.live:
            head.append("#EXT-X-PLAYLIST-TYPE:VOD")
        head.append(bump)
        return "\n".join(head)

    def add_cue_tag(self, chunk,seg_time):
        """
        add_cue_tag adds SCTE-35 tags,
        handles break auto returns,
        and adds discontinuity tags as needed.
        """
        if self.scte35.break_timer is not None:
            if self.scte35.break_timer+seg_time > self.scte35.break_duration:
                self.scte35.break_timer = None
                self.scte35.cue_state="IN"
        tag = self.scte35.mk_cue_tag()
        if tag:
            if self.scte35.cue_state in ["OUT", "IN"]:
                chunk.add_tag("#EXT-X-DISCONTINUITY", None)
            kay = tag
            vee = None
            if ":" in tag:
                kay, vee = tag.split(":", 1)
            chunk.add_tag(kay, vee)
            print(kay, vee)

    def _chk_pdt_flag(self, chunk):
        if self.program_date_time_flag:
            iso8601 = f"{datetime.datetime.utcnow().isoformat()}Z"
            chunk.add_tag("#Iframe", f"{self.started}")
            chunk.add_tag("#EXT-X-PROGRAM-DATE-TIME", f"{iso8601}")

    def _write_segment(self):
        seg_name = f"seg{self.segnum}.ts"
        seg_time = self.next_start - self.started
        with open(seg_name, "wb") as seg:
            seg.write(self.active_segment.getbuffer())
        chunk = Chunk(seg_name, self.segnum)
        self.add_cue_tag(chunk,seg_time)
        self._chk_pdt_flag(chunk)
        chunk.add_tag("#EXTINF", f"{seg_time:.6f},")
        self.window.slide_panes(chunk)
        self._write_m3u8()
        self._start_next_start()
        if self.scte35.break_timer is not None:
            self.scte35.break_timer += seg_time
        self.scte35.chk_cue_state()

    def _write_m3u8(self):
        if self.live:
            self._discontinuity_seq_plus_one()
        with open(self.m3u8, "w+") as m3u8:
            m3u8.write(self._header())
            m3u8.write(self.window.all_panes())
            self.segnum += 1
            if not self.live:
                m3u8.write("#EXT-X-ENDLIST")
        self.active_segment = io.BytesIO()

    def load_sidecar(self, pid):
        """
        load_sidecar reads (pts, cue) pairs from
        the sidecar file and loads them into X9K3.sidecar
        if live, blank out the sidecar file after cues are loaded.
        """
        if self.sidecar_file:
            with reader(self.sidecar_file) as sidefile:
                for line in sidefile:
                    line = line.decode().strip().split("#", 1)[0]
                    if len(line):
                        pts, cue = line.split(",", 1)
                        pts = float(pts)
                        if pts >= self.pid2pts(pid):
                            if [pts, cue] not in self.sidecar:
                                self.sidecar.append([pts, cue])
                                self.sidecar = deque(
                                    sorted(self.sidecar, key=itemgetter(0))
                                )
                sidefile.close()
            if self.live:
                with open(self.sidecar_file, "w") as scf:
                    scf.close()

    def chk_sidecar_cues(self, pid):
        """
        chk_sidecar_cues checks the insert pts time
        for the next sidecar cue and inserts the cue if needed.
        """
        if self.sidecar:
            if self.sidecar[0][0] <= self.pid2pts(pid):
                raw = self.sidecar.popleft()[1]
                self.scte35.cue = Cue(raw)
                self.scte35.cue.decode()
                self._chk_cue_time(pid)

    def _discontinuity_seq_plus_one(self):
        if "DISCONTINUITY" in self.window.panes[0][2]:
            self.discontinuity_sequence += 1
        if "DISCONTINUITY" in self.window.panes[-1][2]:
            self._reset_stream()

    def _reset_stream(self):
        self.started = None
        self.next_start = None

    def _start_next_start(self, pts=None):
        if pts is not None:
            self.started = pts
        else:
            self.started = self.next_start
        self.next_start = self.started + self.seconds

    def chk_slice_point(self, now):
        """
        chk_slice_time checks for the slice point
        of a segment eoither buy self.seconds
        or by self.scte35.cue_time
        """
        if self.scte35.cue_time:
            if now >= self.scte35.cue_time >= self.next_start:
                self.next_start = self.scte35.cue_time
                self._write_segment()
                self.scte35.cue_time = None
                self.scte35.mk_cue_state()
        else:
            if now >= self.next_start:
                self.next_start = now
                self._write_segment()

    def _chk_cue_time(self, pid):
        """
        _chk_cue checks for SCTE-35 cues
        and inserts a tag at the time
        the cue is received.
        """
        if self.scte35.cue:
            pts_adjust = self.scte35.cue.info_section.pts_adjustment
            if "pts_time" in self.scte35.cue.command.get():
                self.scte35.cue_time = self.scte35.cue.command.pts_time+pts_adjust
            else:
                self.scte35.cue_time = self.pid2pts(pid)+pts_adjust

    @staticmethod
    def _rai_flag(pkt):
        return pkt[5] & 0x40

    def shulga_mode(self, pkt, now):
        """
        shulga_mode iframe detection
        """
        if self._rai_flag(pkt):
            chk_slice_point(self, now)

    def _parse_scte35(self, pkt, pid):
        cue = super()._parse_scte35(pkt, pid)
        if cue:
            cue.decode()
            cue.show()
            self.scte35.cue = cue
            self._chk_cue_time(pid)
       #     self._auto_return()
        return cue

    def _parse(self, pkt):
        super()._parse(pkt)
        pkt_pid = self._parse_pid(pkt[1], pkt[2])
        now = self.pid2pts(pkt_pid)
        if not self.started:
            self._start_next_start(pts=now)
        if self._pusi_flag(pkt):
            self.load_sidecar(pkt_pid)
            if self.shulga:
                self.shulga_mode(pkt, now)
            else:
                i_pts = self.iframer.parse(pkt)
                if i_pts:
                    self.chk_sidecar_cues(pkt_pid)
                    self.chk_slice_point(now)
        self.active_segment.write(pkt)

    def do(self):
        """
        do parses packets
        and ensures all the packets are written
        to segments.

        """
        for pkt in self._find_start():
            self._parse(pkt)
        pid = self._parse_pid(pkt[1], pkt[2])
        self.next_start = self.pid2pts(pid)
        self._write_segment()

        

if __name__ == "__main__":

    x9 = ExpX9K3(sys.argv[1])
    x9.do()
