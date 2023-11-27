import traceback


def verbose(message, verbose_checkpoint=None):
    if verbose_checkpoint:
        verbose_checkpoint(message, frame_summary=traceback.extract_stack(limit=2)[0])
