/*

  plugin_oled_display.c - plugin for displaying informations on oled screen.

  Part of grblHAL

  Copyright (c) 2025 Luc LEBOSSE

  grblHAL is free software: you can redistribute it and/or modify
  it under the terms of the GNU General Public License as published by
  the Free Software Foundation, either version 3 of the License, or
  (at your option) any later version.

  grblHAL is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
  GNU General Public License for more programmed.

  You should have received a copy of the GNU General Public License
  along with grblHAL. If not, see <http://www.gnu.org/licenses/>.

*/
#ifdef ARDUINO
#include "../driver.h"
#include "../grbl/hal.h"
#include "../grbl/task.h"
#include "../grbl/system.h"
#include "../grbl/plugins.h"

#else
#include "driver.h"
#include "grbl/hal.h"
#include "grbl/task.h"
#include "grbl/system.h"
#include "grbl/plugins.h"
#endif //ARDUINO


#if DISPLAY_ENABLE == 33

// Include according to the display type
#include "oled_display.h"

#if ETHERNET_ENABLE || WIFI_ENABLE
#ifdef ARDUINO
#include "../networking/networking.h"
#else 
#include "networking/networking.h"
#endif //ARDUINO
#endif //ETHERNET_ENABLE || WIFI_ENABLE

// extern variables
extern char const *const axis_letter[N_AXIS];

// Define plugin version
#define PLUGGIN_DISPLAY_VERSION "1.0.0"
// Define polling delay
#define POLLING_DELAY 800


// --------------------------------------------------------
// Types and Constants
// --------------------------------------------------------


// Define data to display
typedef struct {
    const char *state;
#if ETHERNET_ENABLE || WIFI_ENABLE
    char ip[30];
#endif //ETHERNET_ENABLE || WIFI_ENABLE
    char pos_str[N_AXIS][STRLEN_COORDVALUE + 1];
    char label[N_AXIS][3];
    int8_t end_stop[N_AXIS];
} oled_screen_data_t;

// Global variables
static on_report_options_ptr on_report_options;
static on_state_change_ptr on_state_change;
static oled_screen_data_t screen1;

#if ETHERNET_ENABLE || WIFI_ENABLE
static on_network_event_ptr on_event;
#endif

// --------------------------------------------------------
// Function Prototypes
// --------------------------------------------------------

// Interface functions
static void report_options(bool newopt);
static void onStateChanged(sys_state_t state);
static void polling_task(void *data);


// Public initialization function
void plugin_display_init(void);

// --------------------------------------------------------
// Network Event Handling
// --------------------------------------------------------

#if ETHERNET_ENABLE || WIFI_ENABLE

static void network_event(const char *interface, network_status_t status)
{
    if(on_event){
        on_event(interface, status);
    }
    if((status.changed.ap_started && status.flags.ap_started) || status.changed.ip_aquired) {
        network_info_t *info;

        if((info = networking.get_info(interface))) {
            strcpy(screen1.ip, info->status.ip);
        }
    }
}
#endif //ETHERNET_ENABLE || WIFI_ENABLE

// --------------------------------------------------------
// Report and State Change Handlers
// --------------------------------------------------------

static void report_options(bool newopt)
{
    if (on_report_options){
        on_report_options(newopt);
    }
    if(newopt) {
        hal.stream.write(",DISPLAY");
    } else {
        char buffer[50];
        snprintf(buffer, sizeof(buffer), "%s - (%s %sconnected)", PLUGGIN_DISPLAY_VERSION, display_name(), display_connected() ? "" : "not ");
        report_plugin("Display",buffer);
    }
}

static void onStateChanged(sys_state_t state)
{
    if(on_state_change){
        on_state_change(state);
    }
    switch(state) {
        case STATE_IDLE:
            screen1.state = "IDLE";
            break;
        case STATE_CHECK_MODE:
            screen1.state = "CHECK";
            break;
        case STATE_HOMING:
            screen1.state = "HOME";
            break;
        case STATE_JOG:
            screen1.state = "JOG";
            break;
        case STATE_CYCLE:
            screen1.state = "RUN";
            break;
        case STATE_HOLD:
            screen1.state = "HOLD";
            break;
        case STATE_SAFETY_DOOR:
            screen1.state = "DOOR";
            break;
        case STATE_SLEEP:
            screen1.state = "SLEEP";
            break;
        case STATE_ESTOP:
        case STATE_ALARM:
            screen1.state = "ALARM";
            break;
        case STATE_TOOL_CHANGE:
        default:
            break;
    };
}


/**
 * Polling task for updating display data
 */
static void polling_task(void *data) {
    if (data) {
        display_clear();
    }
    
    // Add next polling
    task_add_delayed(polling_task, NULL, POLLING_DELAY);
    
    // Get endstop status
    if (settings.status_report.pin_state) {
        axes_signals_t lim_pin_state = limit_signals_merge(hal.limits.get_state());
        uint_fast16_t idx = 0;

        lim_pin_state.mask &= AXES_BITMASK;
        while (lim_pin_state.mask && idx < 3) {
            if (lim_pin_state.mask & 0x01) {
                screen1.end_stop[idx] = 1;
            } else {
                screen1.end_stop[idx] = 0;
            }
            idx++;
            lim_pin_state.mask >>= 1;
        }
    }
    
    // Get positions
    float pos[N_AXIS];
    system_convert_array_steps_to_mpos(pos, sys.position);
    for (uint8_t i = 0; i < N_AXIS; i++) {
        if (settings.flags.report_inches) {
            strcpy(screen1.pos_str[i], ftoa(pos[i] * INCH_PER_MM, N_DECIMAL_COORDVALUE_INCH));
        } else {
            strcpy(screen1.pos_str[i], ftoa(pos[i], N_DECIMAL_COORDVALUE_MM));
        }
    }

    // Draw information on display
    display_clear();
    // Top never change
    display_set_font(DISPLAY_FONT_BIG);
    display_set_color(DISPLAY_COLOR_BLACK);  
    // Machine state
    display_draw_string(1, 1, screen1.state);
    
#if ETHERNET_ENABLE || WIFI_ENABLE
    // IP address
    display_set_color(DISPLAY_COLOR_WHITE);
    display_set_font(DISPLAY_FONT_SMALL);
    display_draw_string(128- get_string_width(screen1.ip)-1,2,screen1.ip);
#endif //ETHERNET_ENABLE || WIFI_ENABLE

//TODO: Current positions are for a 128x64 display
//      Need to add a way to handle different display size when added

display_set_color(DISPLAY_COLOR_WHITE);
display_set_font(DISPLAY_FONT_SMALL);
    // Positions

#if N_AXIS >= 5
    // 2 columns for positions
    display_set_font(DISPLAY_FONT_SMALL);
    // Positions
    //X
    display_draw_string(0, 16, screen1.label[0]);
    display_draw_string(60- get_string_width(screen1.pos_str[0]), 16, screen1.pos_str[0]);

    //Y
    display_draw_string(0, 16+12, screen1.label[1]);
    display_draw_string(60- get_string_width(screen1.pos_str[1]), 16+12, screen1.pos_str[1]);

    //Z
    display_draw_string(0, 16+24, screen1.label[2]);
    display_draw_string(60- get_string_width(screen1.pos_str[2]), 16+24, screen1.pos_str[2]);

    //A or U
    display_draw_string(66, 16, screen1.label[3]);
    display_draw_string(127-get_string_width(screen1.pos_str[3]), 16, screen1.pos_str[3]);

    //B or V
    display_draw_string(66, 16+12, screen1.label[4]);
    display_draw_string(127-get_string_width(screen1.pos_str[4]), 16+12, screen1.pos_str[4]);


 #if N_AXIS == 6   
    //C or W
    display_draw_string(66, 16+24, screen1.label[5]);
    display_draw_string(127-get_string_width(screen1.pos_str[5]), 16+24, screen1.pos_str[5]);
#endif //N_AXIS == 6

    // Endstops
    //Draw bottom area
    display_set_color(DISPLAY_COLOR_WHITE);
    display_fill_rect(0, 64-11, 128, 11);
    // Draw endstops in black
    display_set_color(DISPLAY_COLOR_BLACK);
    for (uint8_t i = 0; i < N_AXIS; i++) {
       // is endstop reporting ?
        if (screen1.end_stop[i]!=-1) {
            display_draw_string(1 + (i * 20), 64-10, screen1.label[i]);
            // Draw endstop status
            if (screen1.end_stop[i] == 1) {
               display_fill_rect((2 + (i * 20)  + get_string_width(screen1.label[i])), 64-10, 5, 8);
               
            } else {
               display_draw_rect((2 + (i * 20)  + get_string_width(screen1.label[i])), 64-10, 5, 8);
            }
        } 
            
    }
#else //N_AXIS < 5
uint8_t spacing = 3;
uint16_t x_end_stop_status = 90; 
uint16_t start_x_row = 15;
// 1 row for each position and limit state
#if N_AXIS == 4
    display_set_font(DISPLAY_FONT_SMALL);
#else
    display_set_font(DISPLAY_FONT_SMALL);
    x_end_stop_status = 110;
    start_x_row = 15;
#endif //N_AXIS == 4

#if  N_AXIS == 3
    spacing = 6;
#endif //N_AXIS == 3

#if  N_AXIS == 2
    spacing = 10;
#endif //N_AXIS == 2

#if  N_AXIS == 1
    spacing = 15;
#endif

for (uint8_t i = 0; i < N_AXIS; i++) {

    display_draw_string(start_x_row , 14 + (i* get_font_height() ) + ((i+1)*spacing), screen1.label[i]);
    display_draw_string(x_end_stop_status - 5 - get_string_width(screen1.pos_str[i]), 14 + (i* get_font_height() ) + ((i+1)*(spacing)), screen1.pos_str[i]);

    if (screen1.end_stop[i]!=-1) {
        // Draw endstop status
        if (screen1.end_stop[i] == 1) {
           display_fill_rect( x_end_stop_status, 14 + (i* get_font_height() ) + ((i+1)*spacing), 5, get_font_height()-1);
           
        } else {
           display_draw_rect( x_end_stop_status, 14 + (i* get_font_height() ) + ((i+1)*spacing), 5, get_font_height()-1);
        }
    } 
   
}
#endif //N_AXIS_NB >= 5

    // Update the display
    display_refresh();
}


/**
 * Initialize the OLED display plugin
 */
void display_init(void) {
    // Initialize screen data
    screen1.state = "IDLE";
#if ETHERNET_ENABLE || WIFI_ENABLE
    strcpy(screen1.ip, "0.0.0.0");
#endif

    for (uint8_t i = 0; i < N_AXIS; i++) {
        strcpy(screen1.pos_str[i],"0.000");
        // Initialize labels that will be used for position and endstop
        screen1.label[i][0]=axis_letter[i][0];
        screen1.label[i][1]=':';
        screen1.label[i][2]='\0';
        // Initialize endstop status
        screen1.end_stop[i] = -1; // -1 means not reporting
    }

    // Hook report options
    on_report_options = grbl.on_report_options;
    grbl.on_report_options = report_options;
    
    // Initialize hardware display
    if (display_oled_init()) {
        // Hook state change
        on_state_change = grbl.on_state_change;
        grbl.on_state_change = onStateChanged;

#if ETHERNET_ENABLE || WIFI_ENABLE
        // Hook IP event
        on_event = networking.event;
        networking.event = network_event;
#endif

        // Start polling task
        uint8_t clearscreen = 1;
        task_add_delayed(polling_task, &clearscreen, POLLING_DELAY);
    }
}

#endif //DISPLAY_ENABLE == 33
