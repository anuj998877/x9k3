"""
The SCTE35 class generates SCTE35 HLS tags
"""


import datetime
from timer import Timer
from threefive.encode import mk_splice_insert


class SCTE35:
    """
    A SCTE35 instance is used to hold
    SCTE35 cue data by X9K5.
    """

    def __init__(self):
        self.cue = None
        self.cue_state = None
        self.cue_time = None
        self.tag_method = self.x_daterange
        self.break_timer = Timer()
        self.break_duration = None
        self.event_id = 1

    def mk_auto_return(timestamp):
        """
        mk_auto_return generates a cue
        when a splice insert has the
        break_autp_return flag set.
        """
        evt_id = random.randint(1, 1000)
        cue = mk_splice_insert(evt_id, time_stamp)
        return cue.encode()

    def mk_cue_tag(self):
        """
        mk_cue_tag routes  hls tag creation
        to the appropriate method.
        """
        tag = False
        if self.cue:
            if self.is_cue_in(self.cue):
                self.cue_state = "IN"
            tag = self.tag_method()
        return tag

    def chk_cue_state(self):
        if self.cue_state == "OUT":
            self.cue_state = "CONT"
        if self.cue_state == "IN":
            self.cue_time = None
            self.cue = None
            self.cue_state = None


    def mk_cue_state(self):
        if self.is_cue_out(self.cue):
            self.cue_state= "OUT"
        if self.is_cue_in(self.cue):
            self.cue_state= "IN"

    def x_cue(self):
        """
        #EXT-X-CUE-( OUT | IN | CONT )
        """
        print(self.cue_state)
        if self.cue_state == "OUT":
            # self.break_timer = Timer()
            return f"#EXT-X-CUE-OUT:{self.break_duration}"
        if self.cue_state == "IN":
            return "#EXT-X-CUE-IN"
        if self.cue_state == "CONT":
            return f"#EXT-X-CUE-OUT-CONT:{self.break_timer.elapsed():.6f}/{self.break_duration}"
        return False

    def x_splicepoint(self):
        """
        #EXT-X-SPLICEPOINT-SCTE35
        """
        base = f"#EXT-X-SPLICEPOINT-SCTE35:{self.cue.encode()}"
        if self.cue_state == "OUT":
            return f"{base}"
        if self.cue_state == "IN":
            return f"{base}"
        return False

    def x_scte35(self):
        """
        #EXT-X-SCTE35
        """
        base = f'#EXT-X-SCTE35:CUE="{self.cue.encode()}" '
        if self.cue_state == "OUT":
            return f"{base},CUE-OUT=YES "
        if self.cue_state == "IN":
            return f"{base},CUE-IN=YES "
        if self.cue_state == "CONT":
            return f"{base},CUE-OUT=CONT"
        return False

    def x_daterange(self):
        """
        #EXT-X-DATERANGE
        """
        fbase = f'#EXT-X-DATERANGE:ID="{self.event_id}"'
        iso8601 = f"{datetime.datetime.utcnow().isoformat()}Z"
        fdur = ""
        if self.break_duration:
            fdur = f",PLANNED-DURATION={self.break_duration}"

        if self.cue_state == "OUT":
            fstart = f',START-DATE="{iso8601}"'
            tag = f"{fbase}{fstart}{fdur},SCTE35-OUT={self.cue.encode_as_hex()}"
            self.event_id += 1
            return tag

        if self.cue_state == "IN":
            fstop = f',END-DATE="{iso8601}"'
            tag = f"{fbase}{fstop},SCTE35-IN={self.cue.encode_as_hex()}"
            self.event_id += 1
            return tag
        return False

    def is_cue_out(self, cue):
        """
        is_cue_out checks a Cue instance
        to see if it is a cue_out event.
        Returns True for a cue_out event.
        """
        if cue is not None:
            cmd = cue.command
            if cmd.command_type == 5:
                if cmd.out_of_network_indicator:
                    if cmd.break_duration:
                        self.break_duration = cmd.break_duration
                        return True

            upid_starts = [
                0x10,
                0x20,
                0x22,
                0x30,
                0x32,
                0x34,
                0x36,
                0x38,
                0x3A,
                0x3C,
                0x3E,
                0x44,
                0x46,
            ]
            if cmd.command_type == 6:
                for dsptr in cue.descriptors:
                    if dsptr.tag == 2:
                        if dsptr.segmentation_type_id in upid_starts:
                            if dsptr.segmentation_duration:
                                self.break_duration = dsptr.segmentation_duration
                                return True
            return False

    def is_cue_in(self, cue):
        """
        is_cue_in checks a Cue instance
        to see if it is a cue_in event.
        Returns True for a cue_in event.
        """
        if cue is not None:
            cmd = cue.command
            if cmd.command_type == 5:
                if not cmd.out_of_network_indicator:
                    return True

            upid_stops = [
                0x11,
                0x21,
                0x21,
                0x23,
                0x33,
                0x35,
                0x37,
                0x39,
                0x3B,
                0x3D,
                0x3F,
                0x45,
                0x47,
            ]
            if cmd.command_type == 6:
                for dsptr in cue.descriptors:
                    if dsptr.tag == 2:
                        if dsptr.segmentation_type_id in upid_stops:
                            if self.break_timer.elapsed() >= self.break_duration:
                                return True
        return False
