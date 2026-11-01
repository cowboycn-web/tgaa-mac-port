#include "bc7enc16.h"
void encode_bc7_block(void *out, const void *pixels) {
    static int initialized;
    if (!initialized) { bc7enc16_compress_block_init(); initialized = 1; }
    bc7enc16_compress_block_params params;
    bc7enc16_compress_block_params_init(&params);
    params.m_max_partitions_mode1 = 0;
    params.m_weights[0] = 1;
    params.m_weights[1] = 1;
    params.m_weights[2] = 1;
    params.m_weights[3] = 4;
    bc7enc16_compress_block(out, pixels, &params);
}
