cd 1_host

set debug=0
set unique_id=test
set build_name=DeadEyeAutoAttack
set /p "remote_ip=Remote ip: "

TITLE %remote_ip% %unique_id% %predefined_strategy% %build_name%
call venv\Scripts\activate

:infinity_loop
python poe_2_mapper.py {'script':'maps','REMOTE_IP':'%remote_ip%','unique_id':'%unique_id%','force_reset_temp':False,'custom_strategy':'','predefined_strategy':'%predefined_strategy%','build':'%build_name%'}
REM pause
goto :infinity_loop