cd 1_host

@echo off
set debug=0
set /p "remote_ip=Remote ip: "

TITLE %remote_ip% %predefined_strategy% %build_name%
call venv\Scripts\activate

:infinity_loop
python poe_2_follower.py {'script':'maps','REMOTE_IP':'%remote_ip%','force_reset_temp':False,'custom_strategy':'','predefined_strategy':'%predefined_strategy%','build':'%build_name%'}
goto :infinity_loop