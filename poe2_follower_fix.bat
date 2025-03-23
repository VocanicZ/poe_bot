cd 1_host

set debug=0
set unique_id=เทพไม่กินเผ็ด
set remote_ip=172.18.149.162
set hostname=POE2

REM if you want to use the ip, then REM the next line and -- set remote_ip=
for /f "tokens=2 delims=[]" %%a in ('ping -n 1 %hostname% ^| findstr "["') do set remote_ip=%%a

TITLE %remote_ip% %unique_id% %predefined_strategy% %build_name%
call venv\Scripts\activate

:infinity_loop
python poe_2_follower_fix.py {'script':'maps','REMOTE_IP':'%remote_ip%','unique_id':'%unique_id%','force_reset_temp':False,'custom_strategy':'','predefined_strategy':'%predefined_strategy%','build':'%build_name%'}
goto :infinity_loop
