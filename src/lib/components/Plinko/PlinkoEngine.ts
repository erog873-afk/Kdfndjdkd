import { binPayouts } from '$lib/constants/game';
import {
  rowCount,
  winRecords,
  riskLevel,
  betAmount,
  balance,
  betAmountOfExistingBalls,
  totalProfitHistory,
  difficulty,
} from '$lib/stores/game';
import { addHistory } from '$lib/stores/history';
import type { RiskLevel, RowCount } from '$lib/types';
import { getRandomBetween } from '$lib/utils/numbers';
import { getRulesHash, takeNonce } from '$lib/utils/fair';
import { fetchServerBalance, isServerMode, serverPlaceBet, serverSettle } from '$lib/utils/api';
import Matter, { type IBodyDefinition } from 'matter-js';
import { get } from 'svelte/store';
import { v4 as uuidv4 } from 'uuid';

type BallFrictionsByRowCount = {
  friction: NonNullable<IBodyDefinition['friction']>;
  frictionAirByRowCount: Record<RowCount, NonNullable<IBodyDefinition['frictionAir']>>;
};

/**
 * Engine for rendering the Plinko game using [matter-js](https://brm.io/matter-js/).
 *
 * The engine will read/write data to Svelte stores during game state changes.
 */
class PlinkoEngine {
  /**
   * The canvas element to render the game to.
   */
  private canvas: HTMLCanvasElement;

  /**
   * A cache value of the {@link betAmount} store for faster access.
   */
  private betAmount: number;
  /**
   * A cache value of the {@link rowCount} store for faster access.
   */
  private rowCount: RowCount;
  /**
   * A cache value of the {@link riskLevel} store for faster access.
   */
  private riskLevel: RiskLevel;

  private engine: Matter.Engine;
  private render: Matter.Render;
  private runner: Matter.Runner;

  /**
   * Every pin of the game.
   */
  private pins: Matter.Body[] = [];
  /**
   * Walls are invisible, slanted "guard rails" at the left and right sides of the
   * pin triangle. It prevents balls from falling outside the pin triangle and not
   * hitting a bin.
   */
  private walls: Matter.Body[] = [];
  /**
   * "Sensor" is an invisible body at the bottom of the canvas. It detects whether
   * a ball arrives at the bottom and enters a bin.
   */
  private sensor: Matter.Body;

  /**
   * The x-coordinates of every pin's center in the last row. Useful for calculating
   * which bin a ball falls into.
   */
  private pinsLastRowXCoords: number[] = [];

  /** nonce и seed'ы, зафиксированные в момент ставки, по id шарика. */
  private fairByBall: Record<number, ReturnType<typeof takeNonce>> = {};

  /** Серверный режим: id игры (промис ставки) по id шарика. */
  private serverBets: Record<number, Promise<string | null>> = {};

  static WIDTH = 760;
  static HEIGHT = 620;

  private static PADDING_X = 52;
  private static PADDING_TOP = 80;
  private static PADDING_BOTTOM = 30;

  private static PIN_CATEGORY = 0x0001;
  private static BALL_CATEGORY = 0x0002;

  /**
   * Friction parameters to be applied to the ball body.
   *
   * Higher friction leads to more concentrated distribution towards the center. These numbers
   * are found by trial and error to make the actual weighted bin payout very close to the
   * expected bin payout.
   */
  private static ballFrictions: BallFrictionsByRowCount = {
    friction: 0.5,
    frictionAirByRowCount: {
      8: 0.0395,
      9: 0.041,
      10: 0.038,
      11: 0.0355,
