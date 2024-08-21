import json

class CheckDataType:
    def is_bytes(self, s=None):
        is_bytes: bool = False
        try:
            if isinstance(s, bytes):
                is_bytes = True
        except ValueError:
            pass
        except Exception as e:
            pass
        
        return is_bytes

    def is_hex(self, s=None):
        is_hex: bool = False
        try:
            if self.is_bytes(s):
                s = s.hex()
            int(s, 16)
            is_hex = True
        except ValueError:
            pass
        except Exception as e:
            pass
        
        return is_hex

    def is_json(self, s=None):
        is_json: bool = False
        try:
            if isinstance(s, dict):
                is_json = True
            else:
                json.loads(s.decode('utf-8'))
                is_json = True
        except UnicodeDecodeError:
            pass
        except json.decoder.JSONDecodeError:
            pass
        except Exception as e:
            pass
        
        return is_json

    def is_not_empty(self, d=None):
        is_not_empty: bool = True
        if d in [0, None, "", "null", "Null", {}]:
            is_not_empty = False
        
        return is_not_empty
