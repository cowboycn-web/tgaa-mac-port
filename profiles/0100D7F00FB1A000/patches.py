"""Japanese 1.0.0: keep handheld input while rendering at 1920 × 1080.

The game copies its chosen render size at main+0x727c78, then passes the copy
to NVN WindowSetCrop at main+0x728104. The small trampoline lives in the
zero-filled gap between the main text and rodata segments. The host must also
map normalized mouse touches to 1920 × 1080 (DM_TOUCH_1080=1).
"""

CUTS = {
    'd871b992e95b71c541ddc834f63c664b': [
        (0x727c78, '68265b29', '2e980314',
         'use a 1080p render-size trampoline while retaining handheld input mode'),
        (0x80dd30, '00000000000000000000000000000000',
         '08f080520987805268261b29d067fc17',
         'set render size to 1920x1080 and resume the original initialization'),
    ],
}
