from pydantic import BaseModel,Field,model_validator
class PairedStudyInput(BaseModel):
 code:str=Field(min_length=2,max_length=40,pattern=r'^[A-Z0-9-]+$')
 name:str=Field(min_length=3,max_length=120)
 period:str=Field(min_length=3,max_length=60)
 description:str=Field(default='',max_length=1600)
class PairedLayerInput(BaseModel):
 code:str=Field(min_length=2,max_length=40,pattern=r'^[A-Z0-9-]+$')
 name:str=Field(min_length=2,max_length=120)
 sequence:int=Field(strict=True,ge=0,le=7)
 description:str=Field(default='',max_length=1200)
class PairedCellInput(BaseModel):
 layer_code:str=Field(min_length=1,max_length=40)
 a_success:int=Field(strict=True,ge=0,le=1)
 a_failure:int=Field(strict=True,ge=0,le=1)
 b_success:int=Field(strict=True,ge=0,le=1)
 b_failure:int=Field(strict=True,ge=0,le=1)
 @model_validator(mode='after')
 def one_outcome_each(self):
  if self.a_success+self.a_failure!=1 or self.b_success+self.b_failure!=1:
   raise ValueError('每种封装在每层恰有一次成功且一次失败记录')
  return self
class PairedPieceInput(BaseModel):
 code:str=Field(min_length=1,max_length=40)
 source:str=Field(default='',max_length=160)
 cells:list[PairedCellInput]=Field(min_length=2,max_length=8)
class PairedStudyContent(BaseModel):
 """整份配对底稿一次性写入（最多60片、2..8层），用于冻结逐片明细。"""
 study:PairedStudyInput
 layers:list[PairedLayerInput]=Field(min_length=2,max_length=8)
 pieces:list[PairedPieceInput]=Field(min_length=1,max_length=60)
 @model_validator(mode='after')
 def cross_check(self):
  layer_codes=[x.code for x in self.layers]
  if len(set(layer_codes))!=len(layer_codes):raise ValueError('湿度层编号重复')
  piece_codes=[x.code for x in self.pieces]
  if len(set(piece_codes))!=len(piece_codes):raise ValueError('试片编号重复')
  layer_set=set(layer_codes)
  for p in self.pieces:
   cell_layers=[c.layer_code for c in p.cells]
   if set(cell_layers)!=layer_set or len(cell_layers)!=len(layer_set):
    raise ValueError('每片必须为每个湿度层各提供一条且仅一条封装成败记录')
  return self
class PairedRunInput(BaseModel):
 name:str=Field(min_length=3,max_length=160)
 study_id:int=Field(gt=0,strict=True)
 alpha:float=Field(default=.05,ge=.001,le=.1,strict=True,allow_inf_nan=False)
