export type UnitKind = 'department' | 'class';

export interface UnitSummary {
  id: string;
  name: string;
  kind: UnitKind;
  is_active: boolean;
}

export interface Unit extends UnitSummary {
  org_id: string;
  created_at: string;
  updated_at: string;
}

export interface CreateUnitRequest {
  name: string;
  kind: UnitKind;
}

export interface UpdateUnitRequest {
  name?: string;
  kind?: UnitKind;
  is_active?: boolean;
}
