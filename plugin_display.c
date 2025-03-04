/*

  plugin_display.c - plugin for displaying informations on oled screen.

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
#else
#include "driver.h"
#include "grbl/hal.h"
#include "grbl/task.h"
#include "grbl/system.h"
#endif //ARDUINO
#include "grbl/report.h"

#define POLLING_DELAY 800

#if defined(PLUGIN_DISPLAY_ENABLE)
#include "plugin_display.h"
// Include according to the display type
#include "oled_display.h"
// Include configuration for display type
#include "ssd1306_i2c.h"

#if ETHERNET_ENABLE || WIFI_ENABLE
#ifdef ARDUINO
#include "../networking/networking.h"
#else 
#include "networking/networking.h"
#endif //ARDUINO
#endif //ETHERNET_ENABLE || WIFI_ENABLE

// --------------------------------------------------------
// Types and Constants
// --------------------------------------------------------


// Define data to display
typedef struct {
    const char *state;
#if ETHERNET_ENABLE || WIFI_ENABLE
    char ip[30];
#endif //ETHERNET_ENABLE || WIFI_ENABLE
    float pos[N_AXIS];
    char pos_str[N_AXIS][STRLEN_COORDVALUE + 1];
    bool end_stop[N_AXIS];
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
        report_plugin("Oled Display", PLUGGIN_DISPLAY_VERSION);
    }
}

static void onStateChanged(sys_state_t state)
{
    if(on_state_change){
        on_state_change(state);
    }
    switch(state) {
        case STATE_IDLE:
            screen1.state = "Idle";
            break;
        case STATE_CHECK_MODE:
            screen1.state = "Check";
            break;
        case STATE_HOMING:
            screen1.state = "Home";
            break;
        case STATE_JOG:
            screen1.state = "Jog";
            break;
        case STATE_CYCLE:
            screen1.state = "Run";
            break;
        case STATE_HOLD:
            screen1.state = "Hold";
            break;
        case STATE_SAFETY_DOOR:
            screen1.state = "Door";
            break;
        case STATE_SLEEP:
            screen1.state = "Sleep";
            break;
        case STATE_ESTOP:
        case STATE_ALARM:
            screen1.state = "Alarm";
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
                screen1.end_stop[idx] = true;
            } else {
                screen1.end_stop[idx] = false;
            }
            idx++;
            lim_pin_state.mask >>= 1;
        }
    }
    
    // Get positions
    system_convert_array_steps_to_mpos(screen1.pos, sys.position);
    for (uint8_t i = 0; i < N_AXIS; i++) {
        if (settings.flags.report_inches) {
            strcpy(screen1.pos_str[i], ftoa(screen1.pos[i] * INCH_PER_MM, N_DECIMAL_COORDVALUE_INCH));
        } else {
            strcpy(screen1.pos_str[i], ftoa(screen1.pos[i], N_DECIMAL_COORDVALUE_MM));
        }
    }

    // Draw information on display
    display_set_font(DISPLAY_FONT_SMALL);
    
#if ETHERNET_ENABLE || WIFI_ENABLE
    // IP address
   // display_draw_string(64, 0, "222.222.222.222");
    //report_info((void *)screen1.ip);
    //display_draw_string(0, 40, "X:9999.999OY:9999.999O");

#endif //ETHERNET_ENABLE || WIFI_ENABLE
    
    // Machine state
    display_set_font(DISPLAY_FONT_BIG);
    display_draw_string(0, 0, "ALARM");
    display_set_font(DISPLAY_FONT_SMALL);
    display_draw_string(128- get_string_width("222.222.222.222"),0,"222.222.222.222" );
    display_set_font(DISPLAY_FONT_SMALL);
    // Positions
    display_draw_string(0, 16, "X:9999.123");
    display_draw_string(0, 16+12, "Y:1234.999");
    display_draw_string(0, 16+24, "Z:9999.123");
    display_draw_string(64, 16, "A:5678.999");
    display_draw_string(64, 16+12, "B:9999.567");
    display_draw_string(64, 16+24, "C:9999.000");


    // Endstops
    display_draw_string(0, 64-12, "X:0 Y:0 Z:0 A:0 B:0 C:0");
   
    // Update the display
    display_refresh();
}


/**
 * Initialize the OLED display plugin
 */
void plugin_display_init(void) {
    // Initialize screen data
    screen1.state = "IDLE";
#if ETHERNET_ENABLE || WIFI_ENABLE
    strcpy(screen1.ip, "0.0.0.0");
#endif
    memset(screen1.pos, 0, sizeof(screen1.pos));
    memset(screen1.end_stop, 0, sizeof(screen1.end_stop));
    memset(screen1.pos_str, 0, sizeof(screen1.pos_str));

    // Hook report options
    on_report_options = grbl.on_report_options;
    grbl.on_report_options = report_options;
    
    // Initialize hardware display
    if (display_init()) {
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

#endif //PLUGIN_DISPLAY_ENABLE
