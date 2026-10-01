<template>
  <div ref="canvasContainer" class="w-full h-full absolute inset-0 z-0 pointer-events-none opacity-60 mix-blend-screen"></div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import * as THREE from 'three'

const canvasContainer = ref(null)

onMounted(() => {
  const container = canvasContainer.value
  
  const scene = new THREE.Scene()
  
  const camera = new THREE.PerspectiveCamera(75, container.clientWidth / container.clientHeight, 0.1, 1000)
  camera.position.z = 6
  
  const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true })
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
    if (!container) return
    camera.aspect = container.clientWidth / container.clientHeight
    camera.updateProjectionMatrix()
    renderer.setSize(container.clientWidth, container.clientHeight)
  }
  
  window.addEventListener('resize', handleResize)
  
  onBeforeUnmount(() => {
    cancelAnimationFrame(animationId)
    window.removeEventListener('resize', handleResize)
    renderer.dispose()
    geometry.dispose()
    material.dispose()
  })
})
</script>
