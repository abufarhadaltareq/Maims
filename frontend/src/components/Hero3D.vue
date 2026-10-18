<template>
  <div ref="canvasContainer" class="w-full h-full absolute inset-0 z-0 pointer-events-none" :style="{ opacity: siteStore.hero3DOpacity / 100, mixBlendMode: siteStore.hero3DBlend ? 'screen' : 'normal' }"></div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { useSiteStore } from '../stores/site'

const canvasContainer = ref(null)
const siteStore = useSiteStore()

// Teardown handles, collected while onMounted runs asynchronously and released
// by a hook registered here during setup.
let disposeScene = null

onMounted(async () => {
  const container = canvasContainer.value
  if (!container) return

  // Three.js is ~400 kB. Importing it statically put the whole WebGL library in
  // the home page's chunk and blocked first paint; loading it after mount lets
  // the hero text render and the page become interactive first.
  let THREE
  try {
    THREE = await import('three')
  } catch (err) {
    // Decorative animation only — a failed import must not break the page.
    console.warn('3D hero unavailable:', err)
    return
  }

  // The component can be unmounted while the dynamic import was in flight;
  // then the container is gone and there is nothing to render into.
  if (!canvasContainer.value) return

  let renderer
  try {
    const scene = new THREE.Scene()

    const camera = new THREE.PerspectiveCamera(75, container.clientWidth / container.clientHeight, 0.1, 1000)
    camera.position.z = 6

    renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true })
    renderer.setSize(container.clientWidth, container.clientHeight)
    renderer.setPixelRatio(window.devicePixelRatio)
    container.appendChild(renderer.domElement)

    const geometry = new THREE.IcosahedronGeometry(2, 0)
    const material = new THREE.MeshPhysicalMaterial({
      color: 0xffffff,
      metalness: 0.9,
      roughness: 0.1,
      transmission: 0.9,
      ior: 1.5,
      thickness: 0.5,
      wireframe: true
    })

    const mesh = new THREE.Mesh(geometry, material)
    scene.add(mesh)

    // Floating accent orbs that drift in front of the wireframe, giving the
    // hero depth without competing with the slide image.
    const orbMat = new THREE.MeshBasicMaterial({ color: 0x0ea5e9, transparent: true, opacity: 0.55 })
    const orb1 = new THREE.Mesh(new THREE.SphereGeometry(0.45, 24, 24), orbMat)
    const orb2 = new THREE.Mesh(new THREE.SphereGeometry(0.3, 24, 24), orbMat)
    orb1.position.set(-3.2, 0.8, 1.5)
    orb2.position.set(3.4, -1, 2)
    scene.add(orb1)
    scene.add(orb2)

    // Add some cool glowing spheres
    const sphereGeo = new THREE.SphereGeometry(0.1, 16, 16)
    const sphereMat1 = new THREE.MeshBasicMaterial({ color: 0xff0055 })
    const sphereMat2 = new THREE.MeshBasicMaterial({ color: 0x00d2ff })

    const sphere1 = new THREE.Mesh(sphereGeo, sphereMat1)
    const sphere2 = new THREE.Mesh(sphereGeo, sphereMat2)
    scene.add(sphere1)
    scene.add(sphere2)

    const ambientLight = new THREE.AmbientLight(0xffffff, 0.2)
    scene.add(ambientLight)

    const dirLight = new THREE.DirectionalLight(0xffffff, 2)
    dirLight.position.set(2, 2, 2)
    scene.add(dirLight)

    let animationId
    let time = 0
    const animate = () => {
      animationId = requestAnimationFrame(animate)
      time += 0.01

      mesh.rotation.x += 0.005
      mesh.rotation.y += 0.005

      orb1.position.y = Math.sin(time * 1.6) * 1.2 + 0.8
      orb1.position.x = Math.cos(time * 1.2) * 2.6 - 3.2
      orb2.position.y = Math.cos(time * 1.4) * 1.4 - 1
      orb2.position.x = Math.sin(time * 1.1) * 2.8 + 3.4

      sphere1.position.x = Math.sin(time * 2) * 3
      sphere1.position.y = Math.cos(time * 2) * 3
      sphere1.position.z = Math.sin(time * 2) * 2

      sphere2.position.x = Math.cos(time * 1.5) * 4
      sphere2.position.y = Math.sin(time * 1.5) * 4
      sphere2.position.z = Math.cos(time * 1.5) * 2

      renderer.render(scene, camera)
    }

    animate()

    const handleResize = () => {
      camera.aspect = container.clientWidth / container.clientHeight
      camera.updateProjectionMatrix()
      renderer.setSize(container.clientWidth, container.clientHeight)
    }

    window.addEventListener('resize', handleResize)

    // Registered synchronously during setup — see disposeScene above. Calling
    // onBeforeUnmount from inside onMounted (as this component used to) left no
    // active instance, so the RAF loop, the resize listener and the WebGL
    // context all survived navigation and accumulated on every visit.
    disposeScene = () => {
      cancelAnimationFrame(animationId)
      window.removeEventListener('resize', handleResize)
      renderer.dispose()
      geometry.dispose()
      material.dispose()
      sphereGeo.dispose()
      sphereMat1.dispose()
      sphereMat2.dispose()
      geometry.dispose()
      material.dispose()
      orbMat.dispose()
      orb1.geometry.dispose()
      orb2.geometry.dispose()
      renderer.domElement?.remove()
    }
  } catch (err) {
    // No WebGL context (old GPU, blocklisted driver, headless browser): the
    // hero simply renders without the 3D layer.
    console.warn('3D hero could not start:', err)
    if (renderer?.domElement) renderer.domElement.remove()
  }
})

onBeforeUnmount(() => {
  disposeScene?.()
  disposeScene = null
})
</script>
