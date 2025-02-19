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

#includ

#include "grbl/hal.h"

#if defined(OLED_DISPLAY_ENABLE)
static on_report_options_ptr on_report_options;

static void report_options (bool newopt)
{
    on_report_options(newopt);

    if(!newopt)
        report_plugin("Oled Display", "1.0");
}

void oled_display_init (void)
{
    // hook report options
    on_report_options = grbl.on_report_options;
    grbl.on_report_options = report_options;
}

#endif //OLED_DISPLAY_ENABLE