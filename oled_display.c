/*

  oled_display.c - plugin for displaying informations on oled screen.

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

#if defined(OLED_DISPLAY_ENABLE)
#include "oled_display.h"
static on_report_options_ptr on_report_options;
static on_state_change_ptr on_state_change;

typedef struct {
  const char *state;
  char ip[16];
  double pos[N_AXIS];
  bool end_stop[N_AXIS];
} oled_screen_t;

static oled_screen_t screen1;

#if ETHERNET_ENABLE || WIFI_ENABLE
#ifdef ARDUINO
#include "../networking/networking.h"
#else 
#include "networking/networking.h"
#endif //ARDUINO

static on_network_event_ptr on_event;

static void network_event (const char *interface, network_status_t status)
{
    if(on_event){
      on_event(interface, status);
    }
    
    report_info("network event");
}

#endif //ETHERNET_ENABLE || WIFI_ENABLE

static void report_options (bool newopt)
{
    if (on_report_options){
      on_report_options(newopt);
    }
    if(newopt) {
      hal.stream.write(",DISPLAY");
    } else {
        report_plugin("Oled Display", PLUGGIN_OLED_DISPLAY_VERSION);
    }
}

static void onStateChanged (sys_state_t state)
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

static void polling_task (void *data){
  task_add_delayed(polling_task, NULL, POLLING_DELAY);
  report_info((void *)screen1.state);
  report_info((void *)screen1.ip);
}

void oled_display_init (void)
{
    screen1.state = "IDLE";
    strcpy(screen1.ip, "0.0.0.0");
    memset(screen1.pos, 0, sizeof(screen1.pos));
    memset(screen1.end_stop, 0, sizeof(screen1.end_stop));
    // hook report options
    on_report_options = grbl.on_report_options;
    grbl.on_report_options = report_options;

    // hook state change
    on_state_change = grbl.on_state_change;
    grbl.on_state_change = onStateChanged;

    // hook ip event
    #if ETHERNET_ENABLE || WIFI_ENABLE
    on_event = networking.event;
    networking.event = network_event;
    #endif

    // start polling task
    task_add_delayed(polling_task, NULL, POLLING_DELAY);
}

#endif //OLED_DISPLAY_ENABLE