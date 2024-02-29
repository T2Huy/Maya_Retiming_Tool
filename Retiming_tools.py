from functools import partial

import maya.cmds as cmds
import maya.mel as mel

class Retiming_Utils(object):

    @classmethod
    def retime_keys(cls, retime_value, incremental, move_to_next):
        range_start_time, range_end_time = cls.get_selected_range()
        start_keyframe_time = cls.get_start_keyframe_time(range_start_time)
        last_keyframe_time = cls.get_last_keyframe_time()
        current_time = start_keyframe_time

        new_keyframe_time = [start_keyframe_time]

        while current_time != last_keyframe_time:
            next_keyframe_time = cls.find_keyframe("next", current_time)
            #current_keyframe_values = [start_keyframe_time]

            if incremental:
                time_diff = next_keyframe_time - current_time
                if current_time < range_end_time:
                    time_diff += retime_value
                    if time_diff < 1:
                        time_diff = 1
            else:
                if current_time < range_end_time:
                    time_diff = retime_value
                else:
                    time_diff = next_keyframe_time - current_time

            new_keyframe_time.append(new_keyframe_time[-1] + time_diff)
            current_time = next_keyframe_time

        if len(new_keyframe_time) > 1:
            cls.retime_key_recursive(start_keyframe_time, 0, new_keyframe_time)

        first_keyframe_time = cls.find_keyframe("first")

        if move_to_next and range_start_time >= first_keyframe_time:
            next_keyframe_time = cls.find_keyframe("next", start_keyframe_time)
            cls.set_current_time(next_keyframe_time)
        elif range_end_time > first_keyframe_time:
            cls.set_current_time(start_keyframe_time)
        else:
            cls.set_current_time(range_start_time)

    @classmethod
    def retime_key_recursive(cls, current_time, index, new_keyframe_times):
        if index >= len(new_keyframe_times):
            return

        updated_keyframe_time = new_keyframe_times[index]

        next_keyframe_time = cls.find_keyframe("next", current_time)

        if updated_keyframe_time < next_keyframe_time:
            cls.change_keyframe_time(current_time, updated_keyframe_time)
            cls.retime_key_recursive(next_keyframe_time, index + 1, new_keyframe_times)
        else:
            cls.retime_key_recursive(next_keyframe_time, index + 1, new_keyframe_times)
            cls.change_keyframe_time(current_time, updated_keyframe_time)

    @classmethod
    def set_current_time(cls, time):
        cmds.currentTime(time)

    @classmethod
    def get_selected_range(cls):
        playback_slider = mel.eval("$tempVar = $gPlayBackSlider")
        selected_range = cmds.timeControl(playback_slider, q=True, rangeArray=True)

        return selected_range

    @classmethod
    def find_keyframe(cls, which, time=None):
        kwargs = {"which": which}
        if which in ["next", "previous"]:
            kwargs["time"] = (time,time)

        return cmds.findKeyframe(**kwargs)

    @classmethod
    def change_keyframe_time(cls, current_time, new_time):
        cmds.keyframe(e=True, time=(current_time,current_time), timeChange=new_time)

    @classmethod
    def get_start_keyframe_time(cls, range_start_time):
        start_times = cmds.keyframe(q=True, time=(range_start_time,range_start_time))
        if start_times:
            return start_times[0]

        start_time = cls.find_keyframe("previous", range_start_time)
        return start_time

    @classmethod
    def get_last_keyframe_time(cls):
        return cls.find_keyframe("last")

class RetimingUI(object):

    WINDOW_NAME = "RetimingUIWindow"
    WINDOW_TITLE = "Retiming Tool"

    ABSOlUTE_BUTTON_WIDTH = 70
    RELATIVE_BUTTON_WIDTH = 65

    @classmethod
    def display(cls, development=False):
        if cmds.window(cls.WINDOW_NAME, exists=True):
            cmds.deleteUI(cls.WINDOW_NAME, window=True)

        if development and cmds.windowPref(cls.WINDOW_NAME, exists=True):
            cmds.windowPref(cls.WINDOW_NAME, remove=True)

        cls.main_window = cmds.window(cls.WINDOW_NAME, title=cls.WINDOW_TITLE, sizeable=False, minimizeButton=False, maximizeButton=False)

        main_layout = cmds.formLayout(parent = cls.main_window)

        absolute_retiming_layout = cmds.rowLayout(parent=main_layout, numberOfColumns=6)
        cmds.formLayout(main_layout, e=True, attachForm=(absolute_retiming_layout, "top", 2))
        cmds.formLayout(main_layout, e=True, attachForm=(absolute_retiming_layout, "left", 2))
        cmds.formLayout(main_layout, e=True, attachForm=(absolute_retiming_layout, "right", 2))

        for i in range(1,7):
            label = f"{i}f"
            cmd = partial(cls.retime, i, False)
            cmds.button(parent=absolute_retiming_layout, label=label, width=cls.ABSOlUTE_BUTTON_WIDTH, command=cmd)

        shift_left_layout = cmds.rowLayout(parent=main_layout, numberOfColumns=2)
        cmds.formLayout(main_layout, e=True, attachControl=(shift_left_layout, "top", 2, absolute_retiming_layout))
        cmds.formLayout(main_layout, e=True, attachForm=(shift_left_layout, "left", 2))

        cmds.button(parent=shift_left_layout, label="-2f", width=cls.RELATIVE_BUTTON_WIDTH, command=partial(cls.retime, -2, True))
        cmds.button(parent=shift_left_layout, label="-1f", width=cls.RELATIVE_BUTTON_WIDTH, command=partial(cls.retime, -1, True))

        shift_right_layout = cmds.rowLayout(parent=main_layout, numberOfColumns=2)
        cmds.formLayout(main_layout, e=True, attachControl=(shift_right_layout, "top", 2, absolute_retiming_layout))
        cmds.formLayout(main_layout, e=True, attachControl=(shift_right_layout, "left", 48, shift_left_layout))

        cmds.button(parent=shift_right_layout, label="+1f", width=cls.RELATIVE_BUTTON_WIDTH, command=partial(cls.retime, 1,True))
        cmds.button(parent=shift_right_layout, label="+2f", width=cls.RELATIVE_BUTTON_WIDTH, command=partial(cls.retime, 2,True))

        cls.move_to_next_cb = cmds.checkBox(parent=main_layout, label="Move to next Frame", value=False)
        cmds.formLayout(main_layout, e=True, attachControl=(cls.move_to_next_cb, "top", 4, shift_left_layout))
        cmds.formLayout(main_layout, e=True, attachForm=(cls.move_to_next_cb, "left", 2))

        cmds.showWindow()

    @classmethod
    def retime(cls, value, incremental, *args):
        move_to_next = cmds.checkBox(cls.move_to_next_cb, q=True, value=True)
        Retiming_Utils.retime_keys(value, incremental, move_to_next)


if __name__ == "__main__":
    RetimingUI.display(development=True)
