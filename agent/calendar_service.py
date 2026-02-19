import subprocess
import platform
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from pathlib import Path
import sqlite3


def get_db_path() -> str:
    import sys
    if sys.platform == "win32":
        app_data = Path.home() / "AppData" / "Roaming" / "AcademicAssistant"
    else:
        app_data = Path.home() / ".academicassistant"
    
    app_data.mkdir(parents=True, exist_ok=True)
    return str(app_data / "schedules.db")


def init_schedule_db():
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS schedules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT,
            location TEXT,
            description TEXT,
            participants TEXT,
            reminder_minutes INTEGER DEFAULT 30,
            calendar_event_id TEXT,
            synced_to_calendar INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_schedules_start_time ON schedules (start_time)
    ''')
    
    conn.commit()
    conn.close()


class CalendarService:
    def is_available(self) -> bool:
        raise NotImplementedError
    
    def create_event(self, title: str, start_time: datetime,
                    end_time: datetime = None, description: str = "",
                    location: str = "", reminder_minutes: int = 30) -> Dict[str, Any]:
        raise NotImplementedError
    
    def list_events(self, start_date: datetime = None, 
                   end_date: datetime = None) -> List[Dict[str, Any]]:
        raise NotImplementedError
    
    def delete_event(self, event_id: str) -> Dict[str, Any]:
        raise NotImplementedError


class WindowsCalendarService(CalendarService):
    def is_available(self) -> bool:
        try:
            result = subprocess.run(
                ["powershell", "-Command", 
                 "Get-ItemProperty 'HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\App Paths\\OUTLOOK.EXE' -ErrorAction SilentlyContinue"],
                capture_output=True, text=True, timeout=10
            )
            return result.returncode == 0
        except:
            return False
    
    def create_event(self, title: str, start_time: datetime,
                    end_time: datetime = None, description: str = "",
                    location: str = "", reminder_minutes: int = 30) -> Dict[str, Any]:
        if end_time is None:
            end_time = start_time + timedelta(hours=1)
        
        start_str = start_time.strftime("%m/%d/%Y %H:%M")
        end_str = end_time.strftime("%m/%d/%Y %H:%M")
        
        title_escaped = title.replace('"', "'").replace('\n', ' ')
        desc_escaped = description.replace('"', "'").replace('\n', ' ')[:500] if description else ""
        location_escaped = location.replace('"', "'").replace('\n', ' ') if location else ""
        
        ps_script = f'''
$errorActionPreference = 'Stop'
try {{
    $outlook = New-Object -ComObject Outlook.Application
    $appointment = $outlook.CreateItem(1)
    $appointment.Subject = "{title_escaped}"
    $appointment.Start = "{start_str}"
    $appointment.End = "{end_str}"
    $appointment.Body = "{desc_escaped}"
    $appointment.Location = "{location_escaped}"
    $appointment.ReminderSet = $true
    $appointment.ReminderMinutesBeforeStart = {reminder_minutes}
    $appointment.Save()
    $entryId = $appointment.EntryID
    Write-Output "{{\\"success\\": true, \\"event_id\\": \\"$entryId\\"}}"
    [System.Runtime.Interopservices.Marshal]::ReleaseComObject($appointment) | Out-Null
    [System.Runtime.Interopservices.Marshal]::ReleaseComObject($outlook) | Out-Null
}} catch {{
    Write-Output "{{\\"success\\": false, \\"error\\": \\"$_\\"}}"
}}
'''
        
        try:
            result = subprocess.run(
                ["powershell", "-Command", ps_script],
                capture_output=True, text=True, timeout=30
            )
            
            output = result.stdout.strip()
            if output:
                try:
                    data = json.loads(output)
                    if data.get("success"):
                        return {
                            "success": True,
                            "event_id": data.get("event_id"),
                            "message": "日程已添加到 Outlook 日历"
                        }
                    else:
                        return {
                            "success": False,
                            "error": data.get("error", "未知错误")
                        }
                except json.JSONDecodeError:
                    pass
            
            if "success" in output.lower() or result.returncode == 0:
                return {
                    "success": True,
                    "message": "日程已添加到 Outlook 日历"
                }
            
            return {
                "success": False,
                "error": result.stderr or "PowerShell 执行失败"
            }
            
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "操作超时"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def list_events(self, start_date: datetime = None,
                   end_date: datetime = None) -> List[Dict[str, Any]]:
        if start_date is None:
            start_date = datetime.now()
        if end_date is None:
            end_date = start_date + timedelta(days=30)
        
        start_str = start_date.strftime("%m/%d/%Y")
        end_str = end_date.strftime("%m/%d/%Y")
        
        ps_script = f'''
$errorActionPreference = 'Stop'
try {{
    $outlook = New-Object -ComObject Outlook.Application
    $namespace = $outlook.GetNamespace("MAPI")
    $calendar = $namespace.GetDefaultFolder(9)
    $items = $calendar.Items
    $items.Sort("[Start]")
    $items.IncludeRecurrences = $true
    
    $filter = "[Start] >= '{start_str}' AND [End] <= '{end_str}'"
    $filteredItems = $items.Restrict($filter)
    
    $events = @()
    foreach ($item in $filteredItems) {{
        $events += @{{
            id = $item.EntryID
            title = $item.Subject
            start = $item.Start.ToString("yyyy-MM-dd HH:mm")
            end = $item.End.ToString("yyyy-MM-dd HH:mm")
            location = $item.Location
        }}
    }}
    
    $events | ConvertTo-Json -Depth 2
    [System.Runtime.Interopservices.Marshal]::ReleaseComObject($items) | Out-Null
    [System.Runtime.Interopservices.Marshal]::ReleaseComObject($calendar) | Out-Null
    [System.Runtime.Interopservices.Marshal]::ReleaseComObject($namespace) | Out-Null
    [System.Runtime.Interopservices.Marshal]::ReleaseComObject($outlook) | Out-Null
}} catch {{
    Write-Output "[]"
}}
'''
        
        try:
            result = subprocess.run(
                ["powershell", "-Command", ps_script],
                capture_output=True, text=True, timeout=30
            )
            
            output = result.stdout.strip()
            if output:
                try:
                    return json.loads(output)
                except:
                    pass
            return []
        except:
            return []
    
    def delete_event(self, event_id: str) -> Dict[str, Any]:
        ps_script = f'''
$errorActionPreference = 'Stop'
try {{
    $outlook = New-Object -ComObject Outlook.Application
    $namespace = $outlook.GetNamespace("MAPI")
    $item = $namespace.GetItemFromID("{event_id}")
    $item.Delete()
    Write-Output "{{\\"success\\": true}}"
    [System.Runtime.Interopservices.Marshal]::ReleaseComObject($namespace) | Out-Null
    [System.Runtime.Interopservices.Marshal]::ReleaseComObject($outlook) | Out-Null
}} catch {{
    Write-Output "{{\\"success\\": false, \\"error\\": \\"$_\\"}}"
}}
'''
        
        try:
            result = subprocess.run(
                ["powershell", "-Command", ps_script],
                capture_output=True, text=True, timeout=30
            )
            
            output = result.stdout.strip()
            if output:
                try:
                    return json.loads(output)
                except:
                    pass
            
            return {"success": False, "error": "删除失败"}
        except Exception as e:
            return {"success": False, "error": str(e)}


class LocalScheduleService(CalendarService):
    def __init__(self):
        init_schedule_db()
    
    def is_available(self) -> bool:
        return True
    
    def create_event(self, title: str, start_time: datetime,
                    end_time: datetime = None, description: str = "",
                    location: str = "", reminder_minutes: int = 30,
                    participants: List[str] = None) -> Dict[str, Any]:
        if end_time is None:
            end_time = start_time + timedelta(hours=1)
        
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        now = datetime.now().isoformat()
        participants_json = json.dumps(participants) if participants else "[]"
        
        cursor.execute('''
            INSERT INTO schedules (title, start_time, end_time, location, description, 
                                  participants, reminder_minutes, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (title, start_time.isoformat(), end_time.isoformat(),
              location, description, participants_json, reminder_minutes, now, now))
        
        schedule_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return {
            "success": True,
            "event_id": str(schedule_id),
            "message": "日程已保存到本地"
        }
    
    def list_events(self, start_date: datetime = None,
                   end_date: datetime = None) -> List[Dict[str, Any]]:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        if start_date is None:
            start_date = datetime.now()
        if end_date is None:
            end_date = start_date + timedelta(days=30)
        
        cursor.execute('''
            SELECT id, title, start_time, end_time, location, description,
                   participants, reminder_minutes, synced_to_calendar
            FROM schedules
            WHERE start_time >= ? AND start_time <= ?
            ORDER BY start_time
        ''', (start_date.isoformat(), end_date.isoformat()))
        
        rows = cursor.fetchall()
        conn.close()
        
        events = []
        for row in rows:
            participants = []
            if row[6]:
                try:
                    participants = json.loads(row[6])
                except:
                    pass
            
            events.append({
                "id": row[0],
                "title": row[1],
                "start": row[2],
                "end": row[3],
                "location": row[4],
                "description": row[5],
                "participants": participants,
                "reminder_minutes": row[7],
                "synced": bool(row[8])
            })
        
        return events
    
    def delete_event(self, event_id: str) -> Dict[str, Any]:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM schedules WHERE id = ?', (int(event_id),))
        
        if cursor.rowcount > 0:
            conn.commit()
            conn.close()
            return {"success": True, "message": "日程已删除"}
        else:
            conn.close()
            return {"success": False, "error": "日程不存在"}


class HybridCalendarService(CalendarService):
    def __init__(self):
        self.local_service = LocalScheduleService()
        self.system_service = None
        
        if platform.system() == "Windows":
            self.system_service = WindowsCalendarService()
    
    def is_available(self) -> bool:
        return True
    
    def create_event(self, title: str, start_time: datetime,
                    end_time: datetime = None, description: str = "",
                    location: str = "", reminder_minutes: int = 30,
                    participants: List[str] = None) -> Dict[str, Any]:
        local_result = self.local_service.create_event(
            title, start_time, end_time, description, location,
            reminder_minutes, participants
        )
        
        system_event_id = None
        synced = False
        
        if self.system_service and self.system_service.is_available():
            system_result = self.system_service.create_event(
                title, start_time, end_time, description, location, reminder_minutes
            )
            
            if system_result.get("success"):
                system_event_id = system_result.get("event_id")
                synced = True
                
                if local_result.get("event_id"):
                    self._update_sync_status(local_result["event_id"], system_event_id)
        
        return {
            "success": True,
            "event_id": local_result.get("event_id"),
            "system_event_id": system_event_id,
            "synced_to_calendar": synced,
            "message": "日程已创建" + ("并同步到系统日历" if synced else "")
        }
    
    def _update_sync_status(self, local_id: str, system_event_id: str):
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE schedules 
            SET synced_to_calendar = 1, calendar_event_id = ?
            WHERE id = ?
        ''', (system_event_id, int(local_id)))
        
        conn.commit()
        conn.close()
    
    def list_events(self, start_date: datetime = None,
                   end_date: datetime = None) -> List[Dict[str, Any]]:
        return self.local_service.list_events(start_date, end_date)
    
    def delete_event(self, event_id: str) -> Dict[str, Any]:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT calendar_event_id FROM schedules WHERE id = ?', (int(event_id),))
        row = cursor.fetchone()
        conn.close()
        
        if row and row[0] and self.system_service:
            self.system_service.delete_event(row[0])
        
        return self.local_service.delete_event(event_id)


calendar_service = HybridCalendarService()


async def create_schedule(title: str, start_time: str, end_time: str = None,
                         description: str = "", location: str = "",
                         reminder_minutes: int = 30) -> Dict[str, Any]:
    try:
        start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00').replace(' ', 'T'))
        if not start_dt.tzinfo:
            start_dt = start_dt.replace(tzinfo=None)
    except:
        start_dt = datetime.now() + timedelta(hours=1)
    
    end_dt = None
    if end_time:
        try:
            end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00').replace(' ', 'T'))
            if not end_dt.tzinfo:
                end_dt = end_dt.replace(tzinfo=None)
        except:
            end_dt = start_dt + timedelta(hours=1)
    
    return calendar_service.create_event(
        title=title,
        start_time=start_dt,
        end_time=end_dt,
        description=description,
        location=location,
        reminder_minutes=reminder_minutes
    )


async def list_schedules(start_date: str = None, end_date: str = None) -> Dict[str, Any]:
    start_dt = None
    end_dt = None
    
    if start_date:
        try:
            start_dt = datetime.fromisoformat(start_date)
        except:
            pass
    
    if end_date:
        try:
            end_dt = datetime.fromisoformat(end_date)
        except:
            pass
    
    events = calendar_service.list_events(start_dt, end_dt)
    
    return {
        "success": True,
        "total": len(events),
        "schedules": events
    }


async def delete_schedule(schedule_id: int) -> Dict[str, Any]:
    return calendar_service.delete_event(str(schedule_id))
