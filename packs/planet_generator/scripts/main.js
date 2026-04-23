import { world, system, CommandPermissionLevel, CustomCommandParamType } from '@minecraft/server';
import { ModalFormData } from '@minecraft/server-ui';

const SHELL_THICKNESS = 2;
const MAX_RADIUS = 150;

const PLANETS = {
  'space:sun':     { radius: 30, block: 'glowstone',       name: 'Sun' },
  'space:mercury': { radius: 4, block: 'gray_wool', name: 'Mercury' },
  'space:venus':   { radius: 7,  block: 'sandstone',       name: 'Venus' },
  'space:earth': { radius: 8, block: 'light_blue_wool', name: 'Earth' },
  'space:mars':    { radius: 6,  block: 'red_sandstone',   name: 'Mars' },
  'space:jupiter': { radius: 18, block: 'orange_wool',     name: 'Jupiter' },
  'space:saturn':  { radius: 14, block: 'yellow_wool',     name: 'Saturn', ringBlock: 'white_wool' },
  'space:uranus':  { radius: 11, block: 'cyan_wool',       name: 'Uranus' },
  'space:neptune': { radius: 10, block: 'blue_wool',       name: 'Neptune' },
  'space:pluto': { radius: 2, block: 'blue_ice', name: 'Pluto' },
  'space:haumea': { radius: 3, block: 'gray_wool', name: 'Haumea' },
};

function* sphereJob(dimension, center, radius, blockId) {
  const { x: cx, y: cy, z: cz } = center;
  const inner = radius - SHELL_THICKNESS;
  for (let dx = -radius; dx <= radius; dx++) {
    for (let dy = -radius; dy <= radius; dy++) {
      for (let dz = -radius; dz <= radius; dz++) {
        const dist = Math.sqrt(dx * dx + dy * dy + dz * dz);
        if (dist >= inner && dist <= radius) {
          try { dimension.setBlockType({ x: cx + dx, y: cy + dy, z: cz + dz }, blockId); } catch {}
        }
      }
    }
    yield;
  }
}

// Flat ring in the XZ plane, two bands with a gap between them
function* ringsJob(dimension, center, planetRadius, blockId) {
  const { x: cx, y: cy, z: cz } = center;
  const inner1 = Math.round(planetRadius * 1.3);
  const outer1 = Math.round(planetRadius * 1.7);
  const inner2 = Math.round(planetRadius * 1.85);
  const outer2 = Math.round(planetRadius * 2.2);
  const outerMax = outer2;

  for (let dx = -outerMax; dx <= outerMax; dx++) {
    for (let dz = -outerMax; dz <= outerMax; dz++) {
      const xzDist = Math.sqrt(dx * dx + dz * dz);
      if ((xzDist >= inner1 && xzDist <= outer1) || (xzDist >= inner2 && xzDist <= outer2)) {
        try { dimension.setBlockType({ x: cx + dx, y: cy, z: cz + dz }, blockId); } catch {}
      }
    }
    yield;
  }
}

function spawnPlanet(player, radius, blockId, ringBlockId) {
  const r = typeof radius === 'string' ? parseInt(radius, 10) : radius;
  if (isNaN(r) || r < 1 || r > MAX_RADIUS) {
    player.sendMessage(`§cRadius must be between 1 and ${MAX_RADIUS} (got: ${JSON.stringify(radius)})`);
    return;
  }
  const pos = player.location;
  const dir = player.getViewDirection();
  const center = {
    x: Math.round(pos.x + dir.x * (r + 2)),
    y: Math.round(pos.y + dir.y * (r + 2)),
    z: Math.round(pos.z + dir.z * (r + 2)),
  };
  player.sendMessage(`§aGenerating ${blockId} sphere... radius=${r}`);
  if (ringBlockId) player.sendMessage(`§aGenerating ${ringBlockId} rings...`);
  player.sendMessage(`§7(centered at ${center.x}, ${center.y}, ${center.z})`);
  system.runJob(sphereJob(player.dimension, center, r, blockId));
  if (ringBlockId) system.runJob(ringsJob(player.dimension, center, r, ringBlockId));
}

function showPlanetForm(player, config) {
  const form = new ModalFormData()
    .title(config.name)
    .textField('Planet block', config.block, { defaultValue: config.block });
  if (config.ringBlock !== undefined) {
    form.textField('Ring block', config.ringBlock, { defaultValue: config.ringBlock });
  }
  form.show(player)
    .then(result => {
      if (result.canceled) return;
      const block = (result.formValues[0] || config.block).trim();
      const ringBlock = config.ringBlock !== undefined
        ? (result.formValues[1] || config.ringBlock).trim()
        : undefined;
      spawnPlanet(player, config.radius, block, ringBlock);
    })
    .catch(err => console.error('[Planet] Form error:', String(err)));
}

world.afterEvents.itemUse.subscribe(({ source: player, itemStack }) => {
  const config = PLANETS[itemStack.typeId];
  if (config) showPlanetForm(player, config);
});

system.beforeEvents.startup.subscribe((event) => {
  event.customCommandRegistry.registerCommand(
    {
      name: 'space:planet',
      description: 'Generate a hollow sphere planet in front of you',
      permissionLevel: CommandPermissionLevel.GameDirectors,
      mandatoryParameters: [
        { name: 'radius', type: CustomCommandParamType.Integer, description: 'Radius in blocks (1-150)' },
        { name: 'block', type: CustomCommandParamType.String, description: 'Block ID (e.g. stone, light_blue_wool)' },
      ],
    },
    (origin, radius, block) => {
      const player = origin.sourceEntity;
      if (!player) return;
      spawnPlanet(player, radius, block, undefined);
    }
  );
  console.log('[Planet] /space:planet registered');
});
