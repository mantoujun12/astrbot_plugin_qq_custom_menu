/** 新版机器人菜单配置接口。 */

import { getBridge } from '../bridge'
import { MOCK_ROBOTS } from './mock'
import { toPlain } from './serialize'
import type {
  RobotConfigResponse,
  RobotConfigSavePayload,
} from '../types/robotConfig'

const ROBOTS_ENDPOINT = 'robots'
const IMPORT_ENDPOINT = 'robots/import-legacy'

export async function fetchRobots(): Promise<RobotConfigResponse> {
  const bridge = getBridge()
  if (!bridge) {
    return MOCK_ROBOTS
  }
  return (await bridge.apiGet(ROBOTS_ENDPOINT)) as RobotConfigResponse
}

export async function saveRobots(
  payload: RobotConfigSavePayload,
): Promise<RobotConfigResponse> {
  const bridge = getBridge()
  if (!bridge) {
    throw new Error('no backend: robot config saving is unavailable in local dev')
  }
  return (await bridge.apiPost(
    ROBOTS_ENDPOINT,
    toPlain(payload),
  )) as RobotConfigResponse
}

export async function importLegacyRobots(
  appids: string[],
  version: number,
): Promise<RobotConfigResponse> {
  const bridge = getBridge()
  if (!bridge) {
    throw new Error('no backend: legacy import is unavailable in local dev')
  }
  return (await bridge.apiPost(
    IMPORT_ENDPOINT,
    toPlain({ appids, version }),
  )) as RobotConfigResponse
}
