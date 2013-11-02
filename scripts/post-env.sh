#!/bin/sh
#
# This file is part of crossroad.
# Copyright (C) 2013 Jehan <jehan at girinstud.io>
#
# crossroad is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# crossroad is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with crossroad.  If not, see <http://www.gnu.org/licenses/>.


# CHANGE the prompt to show you are in cross-comp env.
if [ x"$(locale charmap)"x = "xUTF-8x" ]; then
    SYMBOL="✘"
else
    SYMBOL="*"
fi;

# Leave the user override the default crossroads PS1.
if [ "x${CROSSROADS_PS1}x" = "xx" ]; then
    export PS1="${RED}${CROSSROAD_PLATFORM}${SYMBOL}${NORMAL} ${PS1}"
else
    export PS1="${CROSSROADS_PS1}"
fi

echo "Your environment has been set to cross-compile for the '$CROSSROAD_PLATFORM_NICENAME' ($CROSSROAD_PLATFORM) environment."
echo 'Use `crossroad help` to list available commands and `man crossroad` to get a full documentation of crossroad capabilities.'
echo "To exit this cross-compilation environment, simply \`exit\` the current shell session."
