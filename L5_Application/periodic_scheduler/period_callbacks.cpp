/*
 *     SocialLedge.com - Copyright (C) 2013
 *
 *     This file is part of free software framework for embedded processors.
 *     You can use it and/or distribute it as long as this copyright header
 *     remains unmodified.  The code is free for personal use and requires
 *     permission to use in a commercial product.
 *
 *      THIS SOFTWARE IS PROVIDED "AS IS".  NO WARRANTIES, WHETHER EXPRESS, IMPLIED
 *      OR STATUTORY, INCLUDING, BUT NOT LIMITED TO, IMPLIED WARRANTIES OF
 *      MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE APPLY TO THIS SOFTWARE.
 *      I SHALL NOT, IN ANY CIRCUMSTANCES, BE LIABLE FOR SPECIAL, INCIDENTAL, OR
 *      CONSEQUENTIAL DAMAGES, FOR ANY REASON WHATSOEVER.
 *
 *     You can reach the author of this software at :
 *          p r e e t . w i k i @ g m a i l . c o m
 */

/**
 * @file
 * This contains the period callback functions for the periodic scheduler
 *
 * @warning
 * These callbacks should be used for hard real-time system, and the priority of these
 * tasks are above everything else in the system (above the PRIORITY_CRITICAL).
 * The period functions SHOULD NEVER block and SHOULD NEVER run over their time slot.
 * For example, the 1000Hz take slot runs periodically every 1ms, and whatever you
 * do must be completed within 1ms.  Running over the time slot will reset the system.
 */

#include <sensor.h>
#include <stdint.h>
#include "io.hpp"
#include "periodic_callback.h"
#include "stdio.h"
#include "file_logger.h"
#include "eint.h"
#include "utilities.h"
#include "can.h"
#include "_can_dbc/can_dbc.h"

extern uint8_t Sen_val[3];
extern can_msg_t msg1;
#define THRESHOLD 60
/// This is the stack size used for each of the period tasks
const uint32_t PERIOD_TASKS_STACK_SIZE_BYTES = (512 * 4);

/// Called once before the RTOS is started, this is a good place to initialize things once
bool period_init(void)
{
    return true; // Must return true upon success
}

/// Register any telemetry variables
bool period_reg_tlm(void)
{
    // Make sure "SYS_CFG_ENABLE_TLM" is enabled at sys_config.h to use Telemetry
    return true; // Must return true upon success
}


void period_1Hz(void)
{
    LE.off(1);
    LE.off(2);
    LE.off(3);
}

void period_10Hz(void)
{

    msg_hdr_t hdr;
    uint64_t *to;
    SENSOR_TX_SONARS_t from;

    Sen_val[0]=GetLeftSensorReading();

    if(Sen_val[0]<THRESHOLD)
    {
        LE.toggle(1);
    }

    Sen_val[1]=GetMidSensorReading();

    if(Sen_val[1]<THRESHOLD)
    {
        LE.toggle(2);
    }

    Sen_val[2]=GetRightSensorReading();

    if(Sen_val[2]<THRESHOLD)
    {
        LE.toggle(3);
    }

    //msg1.msg_id = 0x001;
    //msg1.frame_fields.data_len = 3;
    //msg1.data.bytes[0] = Sen_val[0];
    //msg1.data.bytes[1] = Sen_val[1];
    //msg1.data.bytes[2] = Sen_val[2];
    //Sen_val[0]= 45;
    //Sen_val[1] = 23;
    //Sen_val[2] = 89;
    from.m0.SENSOR_SONARS_left = Sen_val[0];
    from.m0.SENSOR_SONARS_middle = Sen_val[1];
    from.m0.SENSOR_SONARS_right = Sen_val[2];


    printf("ecode LEFT is: %f\n",from.m0.SENSOR_SONARS_left);
    printf("encode MID is: %f\n",from.m0.SENSOR_SONARS_middle);
    printf("encode RIGHT: %f\n",from.m0.SENSOR_SONARS_right);
    to = (uint64_t *)&msg1.data;
    hdr = SENSOR_TX_SONARS_encode(to, &from);
    msg1.msg_id = hdr.mid;
    msg1.frame_fields.data_len = hdr.dlc;

    CAN_tx(can1, &msg1, 100);

    //printf("Reading LEFT is: %i\n",msg1.data.bytes[0]);
    //printf("Reading MID is: %i\n",msg1.data.bytes[1]);
    //printf("Reading RIGHT is: %i\n",msg1.data.bytes[2]);
    delay_ms(10);

}

void period_100Hz(void)
{


}

void period_1000Hz(void)
{

   // LE.toggle(4);
}
