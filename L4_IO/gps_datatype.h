/*
 * gps_datatype.h
 *
 *  Created on: Oct 27, 2015
 *      Author: RV
 */
// gps data type file //
#ifndef L4_IO_GPS_DATATYPE_H_
#define L4_IO_GPS_DATATYPE_H_


typedef struct gps_data
{
   double UTC_time;
   float Latitude;
   char* NS_indicator;
   float Longitude;
   char* EW_indicator;
   int GPS_qualty_indicator;
   int Satelite_used;
   float HDOP;
   double Altitude;
   int DGPS_statio_ID;
   int checksum;
}gps_data_t;


typedef struct directions{
        int dir;   //0: Left, 1: Right
        int angle;
}direction_t;

#endif /* L4_IO_GPS_DATATYPE_H_ */