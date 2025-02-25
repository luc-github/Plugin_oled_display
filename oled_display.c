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
#else
#include "driver.h"
#include "grbl/hal.h"
#endif //ARDUINO

#if defined(OLED_DISPLAY_ENABLE)
#include "oled_display.h"
static on_report_options_ptr on_report_options;
static on_state_change_ptr on_state_change;

#if ETHERNET_ENABLE || WIFI_ENABLE
#ifdef ARDUINO
#include "../networking/networking.h"
#else 
#include "networking/networking.h"
#endif //ARDUINO

static on_network_event_ptr on_event;

static void network_event (const char *interface, network_status_t status)
{
    if(on_event)
      on_event(interface, status);
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
    if(on_state_change)
      on_state_change(state);
}

static void polling_fn (void *data){

}

void oled_display_init (void)
{
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
    // add polling task
    task_add_delayed(polling_fn, NULL, 500);
}

#endif //OLED_DISPLAY_ENABLE